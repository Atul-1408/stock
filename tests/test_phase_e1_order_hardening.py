"""Phase E.1: Targeted Order Execution Hardening Test Suite.

Validates:
Issue A — Atomic Limit-Price Enforcement:
  1. BUY limit: execution price > limit price is rejected atomically.
  2. SELL limit: execution price < limit price is rejected atomically.
  3. Valid price improvement (BUY below limit, SELL above limit) succeeds.
  4. Non-finite, NaN, inf, zero, or negative prices rejected without state change.
  5. Rejected execution price leaves order in OPEN state for future valid matching.
  6. Direct caller passing a stale/violating price to fill_order_atomic is blocked.

Issue B — Immediate-Or-Cancel (IOC) Semantics:
  7. Immediately executable IOC order fills instantly at order placement.
  8. Non-executable IOC order is cancelled immediately upon placement.
  9. IOC with missing/invalid market data (<= 0) cancels without fabricating prices.
 10. IOC with insufficient buying power is rejected at validation before order creation.
 11. Unfilled IOC order releases cash and share reservations immediately.
 12. Retrying or worker polling cannot fill an already cancelled IOC remainder.
 13. DAY order behavior remains unchanged (stays OPEN across worker passes).
 14. Concurrent cancellation and fill race behavior on IOC orders.

All tests run strictly against isolated temporary SQLite databases.
"""

import concurrent.futures
import json
import math
import os
import sqlite3
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

# Configure isolated environment
os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "phase-e1-hardening-secret-key-32-bytes!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# Standalone fallback: ensure an isolated temporary DB is used
if "DATABASE_PATH" not in os.environ and "DB_PATH" not in os.environ:
    _test_tmp_dir = tempfile.mkdtemp(prefix="phase_e1_test_db_")
    _test_db_path = os.path.join(_test_tmp_dir, "test_phase_e1.db")
    os.environ["DATABASE_PATH"] = _test_db_path
    os.environ["DB_PATH"] = _test_db_path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
import trading_engine
from app import app
from flask_jwt_extended import create_access_token


class TestPhaseE1OrderHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        # Create fresh isolated SQLite database
        self.temp_dir = tempfile.mkdtemp(prefix="phase_e1_case_")
        self.db_path = os.path.join(self.temp_dir, "isolated_phase_e1.db")
        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["DB_PATH"] = self.db_path

        from config import Config
        Config.DB_PATH = self.db_path

        database.init_db()

        # Create isolated test user
        self.user_email = f"trader_e1_{int(time.time() * 1000)}@example.com"
        self.user_id = database.create_user("Trader E1", self.user_email, "hashed_pw_e1")
        database.update_user_balance(self.user_id, 10000.0)

        with app.app_context():
            self.jwt_token = create_access_token(identity=str(self.user_id))
        self.headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }

    def tearDown(self):
        try:
            import gc
            gc.collect()
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    # =========================================================================
    # ISSUE A: ATOMIC LIMIT-PRICE ENFORCEMENT
    # =========================================================================

    def test_a1_buy_limit_price_violation_rejected_atomically(self):
        """BUY limit order rejects execution price exceeding limit price; keeps order OPEN."""
        # User places BUY limit for 10 AAPL @ $150.0 ($1,500 reserved)
        order_id = database.create_order(self.user_id, "AAPL", "BUY", "LIMIT", "CNC", 10.0, 150.0)
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 1500.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 8500.0)

        # Direct caller attempts to fill at $155.0 (> $150.0 limit) -> MUST REJECT
        res = database.fill_order_atomic(order_id, execution_price=155.0)
        self.assertFalse(res["success"])
        self.assertIn("Limit price violation", res["message"])
        self.assertIn("exceeds limit", res["message"])

        # Invariants: Zero partial financial changes; order remains OPEN for future valid fill
        orders = database.get_user_orders(self.user_id)
        self.assertEqual(orders[0]["status"], "OPEN")
        self.assertEqual(database.get_user_balance(self.user_id), 10000.0)
        self.assertEqual(database.get_user_shares(self.user_id, "AAPL"), 0.0)
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 1500.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 8500.0)
        self.assertEqual(len(database.get_transactions_by_user(self.user_id)), 0)

    def test_a2_sell_limit_price_violation_rejected_atomically(self):
        """SELL limit order rejects execution price below limit price; keeps order OPEN."""
        # Establish holding: 10 MSFT @ $300
        database.execute_trade_atomic(self.user_id, "MSFT", "BUY", 10.0, 300.0)

        # Place SELL limit for 5 MSFT @ $320.0
        order_id = database.create_order(self.user_id, "MSFT", "SELL", "LIMIT", "CNC", 5.0, 320.0)

        # Caller attempts to fill at $315.0 (< $320.0 limit) -> MUST REJECT
        res = database.fill_order_atomic(order_id, execution_price=315.0)
        self.assertFalse(res["success"])
        self.assertIn("Limit price violation", res["message"])
        self.assertIn("below limit", res["message"])

        # Invariants: Order remains OPEN; user still owns all 10 shares (5 available, 5 reserved)
        orders = database.get_user_orders(self.user_id, status="OPEN")
        self.assertEqual(len(orders), 1)
        self.assertEqual(database.get_user_shares(self.user_id, "MSFT"), 10.0)
        self.assertEqual(database.get_user_available_shares(self.user_id, "MSFT"), 5.0)
        # Transactions only contains the original BUY
        self.assertEqual(len(database.get_transactions_by_user(self.user_id)), 1)

    def test_a3_valid_price_improvement_succeeds(self):
        """BUY order executes at better (lower) price; SELL order executes at better (higher) price."""
        # 1. BUY limit: limit is $100.0, executes with price improvement at $95.0
        buy_ord = database.create_order(self.user_id, "IMPRV", "BUY", "LIMIT", "CNC", 10.0, 100.0)
        buy_res = database.fill_order_atomic(buy_ord, execution_price=95.0)
        self.assertTrue(buy_res["success"])
        self.assertEqual(buy_res["filled_price"], 95.0)
        self.assertEqual(buy_res["total_value"], 950.0)
        self.assertEqual(database.get_user_shares(self.user_id, "IMPRV"), 10.0)

        # 2. SELL limit: limit is $110.0, executes with price improvement at $115.0
        sell_ord = database.create_order(self.user_id, "IMPRV", "SELL", "LIMIT", "CNC", 5.0, 110.0)
        sell_res = database.fill_order_atomic(sell_ord, execution_price=115.0)
        self.assertTrue(sell_res["success"])
        self.assertEqual(sell_res["filled_price"], 115.0)
        # Realized P&L: 5 * (115.0 - 95.0) = +$100.0
        self.assertEqual(sell_res["realized_pnl"], 100.0)
        self.assertEqual(database.get_user_shares(self.user_id, "IMPRV"), 5.0)

    def test_a4_invalid_non_finite_and_negative_prices_rejected(self):
        """NaN, Infinity, 0, and negative execution prices are rejected cleanly."""
        order_id = database.create_order(self.user_id, "AMZN", "BUY", "LIMIT", "CNC", 2.0, 150.0)

        for bad_price in [-50.0, 0.0, float("nan"), float("inf"), float("-inf"), "not_a_number"]:
            res = database.fill_order_atomic(order_id, execution_price=bad_price)
            self.assertFalse(res["success"])
            self.assertIn("positive finite number", res["message"])

        # Order must still be OPEN
        orders = database.get_user_orders(self.user_id)
        self.assertEqual(orders[0]["status"], "OPEN")
        self.assertEqual(database.get_user_balance(self.user_id), 10000.0)

    def test_a5_matching_engine_stale_result_blocked_by_atomic_guard(self):
        """If market price swings after matching logic checks, fill_order_atomic blocks execution."""
        database.upsert_market_cache({"symbol": "SWING", "last_price": 100.0})
        order_id = database.create_order(self.user_id, "SWING", "BUY", "LIMIT", "CNC", 5.0, 100.0)

        # Simulate caller attempting to execute at $105.0 despite limit being $100.0
        res = database.fill_order_atomic(order_id, execution_price=105.0)
        self.assertFalse(res["success"])
        self.assertIn("Limit price violation", res["message"])

        # Later, market drops to valid price $98.0 -> matching engine succeeds
        database.upsert_market_cache({"symbol": "SWING", "last_price": 98.0})
        fills = trading_engine.match_pending_orders(symbol="SWING")
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0]["filled_price"], 98.0)
        self.assertEqual(database.get_user_shares(self.user_id, "SWING"), 5.0)

    # =========================================================================
    # ISSUE B: IMMEDIATE-OR-CANCEL (IOC) SEMANTICS
    # =========================================================================

    def test_b1_ioc_immediately_executable_fills_synchronously(self):
        """An IOC order whose limit condition is immediately met fills at placement time."""
        # Market price for NVDA is $120.0
        database.upsert_market_cache({"symbol": "NVDA", "last_price": 120.0})

        # Submit IOC BUY limit @ $125.0 (Market <= Limit -> Immediately executable)
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "NVDA",
            "side": "BUY",
            "order_type": "LIMIT",
            "product_type": "CNC",
            "quantity": 10.0,
            "price": 125.0,
            "validity": "IOC"
        })
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn("ioc", data)
        self.assertEqual(data["ioc"]["status"], "FILLED")
        self.assertTrue(data["ioc"]["filled"])

        # Verify order status in database is FILLED
        order_id = data["order_id"]
        orders = database.get_user_orders(self.user_id)
        matching = next(o for o in orders if o["id"] == order_id)
        self.assertEqual(matching["status"], "FILLED")
        self.assertEqual(matching["filled_price"], 120.0)

        # Verify holdings and balance
        self.assertEqual(database.get_user_shares(self.user_id, "NVDA"), 10.0)
        self.assertEqual(database.get_user_balance(self.user_id), 8800.0)  # 10,000 - 1,200
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 0.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 8800.0)

    def test_b2_ioc_non_executable_cancels_immediately(self):
        """An IOC order whose limit condition is not met cancels instantly upon submission."""
        # Market price for TSLA is $200.0
        database.upsert_market_cache({"symbol": "TSLA", "last_price": 200.0})

        # Submit IOC BUY limit @ $180.0 (Market $200 > Limit $180 -> Non-executable)
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "TSLA",
            "side": "BUY",
            "order_type": "LIMIT",
            "product_type": "CNC",
            "quantity": 5.0,
            "price": 180.0,
            "validity": "IOC"
        })
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn("ioc", data)
        self.assertEqual(data["ioc"]["status"], "CANCELLED")
        self.assertFalse(data["ioc"]["filled"])
        self.assertIn("Price condition not met", data["ioc"]["reason"])

        # Order must be CANCELLED in database immediately (not OPEN)
        order_id = data["order_id"]
        orders = database.get_user_orders(self.user_id)
        matching = next(o for o in orders if o["id"] == order_id)
        self.assertEqual(matching["status"], "CANCELLED")

        # Crucial invariant: Reservation is fully released immediately
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 0.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 10000.0)
        self.assertEqual(database.get_user_balance(self.user_id), 10000.0)
        self.assertEqual(database.get_user_shares(self.user_id, "TSLA"), 0.0)

    def test_b3_ioc_missing_market_data_cancels_without_fabricating_price(self):
        """If market price is 0 or unavailable, IOC cancels immediately with zero trade execution."""
        # Symbol with no price cached and mock price returning 0.0
        with unittest.mock.patch("trading_engine.get_current_price", return_value=0.0):
            res = self.client.post("/api/orders", headers=self.headers, json={
                "symbol": "UNKNOWN",
                "side": "BUY",
                "order_type": "LIMIT",
                "product_type": "CNC",
                "quantity": 10.0,
                "price": 50.0,
                "validity": "IOC"
            })
            self.assertEqual(res.status_code, 201)
            data = json.loads(res.data)
            self.assertEqual(data["ioc"]["status"], "CANCELLED")
            self.assertIn("Could not obtain valid market price", data["ioc"]["reason"])

        # Invariants
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 0.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 10000.0)
        self.assertEqual(len(database.get_transactions_by_user(self.user_id)), 0)

    def test_b4_ioc_insufficient_buying_power_rejected_at_validation(self):
        """IOC order exceeding available buying power is rejected at placement before creation."""
        database.update_user_balance(self.user_id, 500.0)

        # Attempt to buy $1,500 of stock via IOC
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "EXPENS",
            "side": "BUY",
            "order_type": "LIMIT",
            "product_type": "CNC",
            "quantity": 10.0,
            "price": 150.0,
            "validity": "IOC"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Insufficient funds / buying power", json.loads(res.data)["message"])

        # No order created
        self.assertEqual(len(database.get_user_orders(self.user_id)), 0)

    def test_b5_ioc_cancelled_remainder_cannot_be_filled_by_later_worker(self):
        """A cancelled IOC order cannot be filled by subsequent matching worker passes."""
        database.upsert_market_cache({"symbol": "RETRY", "last_price": 110.0})

        # Submit non-executable IOC @ $100.0
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "RETRY",
            "side": "BUY",
            "order_type": "LIMIT",
            "product_type": "CNC",
            "quantity": 5.0,
            "price": 100.0,
            "validity": "IOC"
        })
        data = json.loads(res.data)
        order_id = data["order_id"]
        self.assertEqual(data["ioc"]["status"], "CANCELLED")

        # Now market price drops to $95.0 (which would satisfy limit)
        database.upsert_market_cache({"symbol": "RETRY", "last_price": 95.0})

        # Run background worker matching loop
        worker_fills = trading_engine.match_pending_orders(symbol="RETRY")
        self.assertEqual(len(worker_fills), 0, "Worker must never fill a cancelled IOC order")

        # Direct caller also rejected
        direct_res = database.fill_order_atomic(order_id, execution_price=95.0)
        self.assertFalse(direct_res["success"])
        self.assertIn("cannot be filled because current status is 'CANCELLED'", direct_res["message"])

        # Holding remains 0
        self.assertEqual(database.get_user_shares(self.user_id, "RETRY"), 0.0)

    def test_b6_day_order_behavior_remains_intact(self):
        """DAY limit order stays OPEN across price fluctuations and does not cancel immediately."""
        database.upsert_market_cache({"symbol": "DAYSTK", "last_price": 200.0})

        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "DAYSTK",
            "side": "BUY",
            "order_type": "LIMIT",
            "product_type": "CNC",
            "quantity": 5.0,
            "price": 180.0,
            "validity": "DAY"
        })
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertNotIn("ioc", data)

        # Order must be OPEN and reserving $900
        order_id = data["order_id"]
        orders = database.get_user_orders(self.user_id, status="OPEN")
        self.assertEqual(len(orders), 1)
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 900.0)

        # Worker pass at $200 leaves order OPEN
        fills1 = trading_engine.match_pending_orders(symbol="DAYSTK")
        self.assertEqual(len(fills1), 0)
        self.assertEqual(database.get_user_orders(self.user_id, status="OPEN")[0]["status"], "OPEN")

        # Worker pass at $175 fills order
        database.upsert_market_cache({"symbol": "DAYSTK", "last_price": 175.0})
        fills2 = trading_engine.match_pending_orders(symbol="DAYSTK")
        self.assertEqual(len(fills2), 1)
        self.assertEqual(database.get_user_shares(self.user_id, "DAYSTK"), 5.0)

    def test_b7_concurrent_ioc_fill_and_cancel_race_safety(self):
        """Under concurrent execution, IOC fill and cancel are mutually exclusive."""
        database.upsert_market_cache({"symbol": "IOCRACE", "last_price": 100.0})
        order_id = database.create_order(self.user_id, "IOCRACE", "BUY", "LIMIT", "CNC", 5.0, 100.0, validity="IOC")

        def do_fill():
            return database.fill_order_atomic(order_id, 100.0)

        def do_cancel():
            return database.cancel_order(order_id, self.user_id)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_fill = executor.submit(do_fill)
            f_cancel = executor.submit(do_cancel)
            fill_res = f_fill.result()
            cancel_res = f_cancel.result()

        # Exactly one succeeded
        if fill_res.get("success"):
            self.assertFalse(cancel_res)
            self.assertEqual(database.get_user_shares(self.user_id, "IOCRACE"), 5.0)
        else:
            self.assertTrue(cancel_res)
            self.assertEqual(database.get_user_shares(self.user_id, "IOCRACE"), 0.0)


if __name__ == "__main__":
    unittest.main()
