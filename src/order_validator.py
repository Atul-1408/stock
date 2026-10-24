"""Order Validation and Idempotency Guard for Sovereign Intelligence.

Validates order fields, checks numeric ranges, enforces allowed order states,
verifies price freshness, and prevents duplicate submissions.
"""

import math
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

TICKER_PATTERN = re.compile(r"^[A-Za-z0-9.\-_]{1,20}$")
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "SL", "SL-M"}
VALID_VALIDITIES = {"DAY", "IOC", "GTC"}
VALID_PRODUCT_TYPES = {"CNC", "MIS", "NRML"}

MAX_ORDER_QTY = 1_000_000.0
MAX_ORDER_PRICE = 10_000_000.0


class DuplicateOrderDetector:
    """Thread-safe sliding-window cache to detect rapid duplicate order submissions."""

    def __init__(self, window_seconds: float = 2.0):
        self.window_seconds = window_seconds
        self._cache: Dict[Tuple[int, str, str, float, Optional[float]], float] = {}
        self._lock = threading.Lock()

    def is_duplicate(
        self,
        user_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float]
    ) -> bool:
        now = time.time()
        key = (user_id, symbol.upper(), side.upper(), round(quantity, 4), round(price, 4) if price else None)

        with self._lock:
            # Purge expired entries
            expired_keys = [k for k, ts in self._cache.items() if now - ts > self.window_seconds]
            for k in expired_keys:
                del self._cache[k]

            last_ts = self._cache.get(key)
            if last_ts is not None and (now - last_ts) < self.window_seconds:
                return True

            self._cache[key] = now
            return False


duplicate_detector = DuplicateOrderDetector(window_seconds=2.0)


def validate_order_input(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validates user-submitted order data.

    Returns:
        (is_valid, error_message, sanitized_dict)
    """
    if not isinstance(data, dict):
        return False, "Request payload must be a JSON object.", None

    symbol = (data.get("symbol") or data.get("ticker") or "").strip().upper()
    if not symbol or not TICKER_PATTERN.match(symbol):
        return False, "Invalid stock symbol. Must be 1-20 alphanumeric characters.", None

    side = (data.get("side") or data.get("action") or "").strip().upper()
    if side not in VALID_SIDES:
        return False, f"Invalid order side '{side}'. Must be BUY or SELL.", None

    order_type = (data.get("order_type") or "MARKET").strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        return False, f"Invalid order type '{order_type}'. Must be MARKET, LIMIT, SL, or SL-M.", None

    product_type = (data.get("product_type") or "CNC").strip().upper()
    if product_type not in VALID_PRODUCT_TYPES:
        product_type = "CNC"

    validity = (data.get("validity") or "DAY").strip().upper()
    if validity not in VALID_VALIDITIES:
        validity = "DAY"

    raw_qty = data.get("quantity") or data.get("shares")
    if raw_qty is None:
        return False, "Quantity is required.", None

    try:
        qty = float(raw_qty)
    except (ValueError, TypeError):
        return False, "Quantity must be a valid numeric value.", None

    if not math.isfinite(qty) or math.isnan(qty) or math.isinf(qty):
        return False, "Quantity must be a finite number.", None

    if qty <= 0:
        return False, "Quantity must be greater than zero.", None

    if qty > MAX_ORDER_QTY:
        return False, f"Quantity exceeds maximum allowable limit of {MAX_ORDER_QTY:,.0f}.", None

    # Price validation
    raw_price = data.get("price")
    limit_price: Optional[float] = None
    if raw_price is not None:
        try:
            limit_price = float(raw_price)
        except (ValueError, TypeError):
            return False, "Price must be a valid numeric value.", None

        if not math.isfinite(limit_price) or math.isnan(limit_price) or math.isinf(limit_price):
            return False, "Price must be a finite number.", None

        if limit_price <= 0:
            return False, "Price must be greater than zero.", None

        if limit_price > MAX_ORDER_PRICE:
            return False, f"Price exceeds maximum allowable limit of ${MAX_ORDER_PRICE:,.2f}.", None

    if order_type == "LIMIT" and (limit_price is None or limit_price <= 0):
        return False, "Limit price is required for LIMIT orders.", None

    # Trigger price validation
    raw_trigger = data.get("trigger_price")
    trigger_price: Optional[float] = None
    if raw_trigger is not None:
        try:
            trigger_price = float(raw_trigger)
        except (ValueError, TypeError):
            return False, "Trigger price must be a valid numeric value.", None

        if not math.isfinite(trigger_price) or math.isnan(trigger_price) or math.isinf(trigger_price):
            return False, "Trigger price must be a finite number.", None

        if trigger_price <= 0:
            return False, "Trigger price must be greater than zero.", None

    if order_type in ("SL", "SL-M") and (trigger_price is None or trigger_price <= 0):
        return False, f"Trigger price is required for {order_type} orders.", None

    sanitized = {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "product_type": product_type,
        "validity": validity,
        "quantity": qty,
        "price": limit_price,
        "trigger_price": trigger_price,
    }
    return True, None, sanitized


def is_price_recent(updated_at_str: Optional[str], max_age_hours: float = 72.0) -> bool:
    """Return True if price timestamp is within max_age_hours, False if stale."""
    if not updated_at_str:
        return False
    try:
        clean_str = updated_at_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - dt
        return age.total_seconds() <= (max_age_hours * 3600)
    except Exception:
        return False
