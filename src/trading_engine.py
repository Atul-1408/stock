import yfinance as yf
import logging
logger = logging.getLogger("stock_sense.trading_engine")
from database import (
    get_user_balance,
    update_user_balance,
    get_user_shares,
    get_user_portfolio,
    update_portfolio_item,
    delete_portfolio_item,
    add_transaction
)

def get_current_price(ticker: str) -> Optional[float]:
    """Get latest price using market data cache or live yfinance fallback.
    Rejects stale cache prices during market hours (> Config.MAX_PRICE_AGE_SECONDS).
    Returns price as float, or None if unavailable.
    """
    from config import Config
    from order_validator import is_price_recent, is_market_hours
    import database
    from datetime import datetime, timezone

    ticker_upper = ticker.strip().upper()
    try:
        md = database.get_market_data(ticker_upper)
        if md and md.get('last_price') and float(md['last_price']) > 0:
            updated_at = md.get('updated_at')
            if is_market_hours(ticker_upper):
                if is_price_recent(updated_at, max_age_seconds=Config.MAX_PRICE_AGE_SECONDS):
                    return float(md['last_price'])
                else:
                    logger.info(f"Market data cache for {ticker_upper} is stale ({updated_at}). Falling back to live fetch.")
            else:
                return float(md['last_price'])
    except Exception as e:
        logger.warning(f"Error reading market data cache for {ticker_upper}: {e}")

    try:
        stock = yf.Ticker(ticker_upper)
        data = stock.history(period='1d')
        if not data.empty and 'Close' in data.columns and not data['Close'].empty:
            price = float(data['Close'].iloc[-1])
            if price > 0:
                try:
                    database.save_market_data({
                        'symbol': ticker_upper,
                        'last_price': price,
                        'open_price': float(data['Open'].iloc[-1]) if 'Open' in data.columns else price,
                        'high_price': float(data['High'].iloc[-1]) if 'High' in data.columns else price,
                        'low_price': float(data['Low'].iloc[-1]) if 'Low' in data.columns else price,
                        'prev_close': price,
                        'volume': int(data['Volume'].iloc[-1]) if 'Volume' in data.columns else 0,
                        'change_pct': 0.0,
                        'last_trade_time': datetime.now(timezone.utc).isoformat()
                    })
                except Exception:
                    pass
                return price
        return None
    except Exception as e:
        logger.error(f"Error fetching live price for {ticker_upper}: {e}")
        return None

def execute_trade(user_id: int, ticker: str, action: str, shares: float, sentiment_score=None, sentiment_label=None):
    """
    Executes a paper trade with atomic balance and portfolio validation.
    Returns: {'success': bool, 'data': dict, 'message': str}
    """
    import math
    from database import execute_trade_atomic

    ticker = ticker.strip().upper()
    action = action.strip().upper()

    try:
        shares = float(shares)
    except (ValueError, TypeError):
        return {"success": False, "message": "Shares must be a valid number."}

    if not math.isfinite(shares) or math.isnan(shares) or math.isinf(shares) or shares <= 0:
        return {"success": False, "message": "Shares must be greater than zero."}

    if shares > 1_000_000.0:
        return {"success": False, "message": "Quantity exceeds maximum allowable limit of 1,000,000."}

    price = get_current_price(ticker)
    if price is None or price <= 0:
        return {"success": False, "status_code": 503, "message": "Price unavailable"}

    result = execute_trade_atomic(
        user_id=user_id,
        symbol=ticker,
        side=action,
        quantity=shares,
        execution_price=price,
        order_type='MARKET',
        product_type='CNC',
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label
    )

    if not result.get("success"):
        return {"success": False, "message": result.get("message", "Trade execution failed.")}

    updated_portfolio = get_portfolio_summary(user_id)
    final_balance = result.get('new_balance')

    return {
        "success": True, 
        "message": f"Successfully {action.lower()}ed {shares} shares of {ticker}.",
        "data": {
            "portfolio": updated_portfolio,
            "balance": final_balance,
            "order_id": result.get("order_id")
        }
    }

def get_portfolio_summary(user_id: int):
    """Fetch user portfolio with live P&L calculation and strict price availability handling."""
    from database import (
        get_user_portfolio,
        get_user_buying_power,
        get_user_reserved_cash,
        get_user_reserved_shares,
        get_user_balance,
        get_closed_trades,
    )

    portfolio = get_user_portfolio(user_id)
    summary = []
    total_invested_sum = 0.0

    for holding in portfolio:
        ticker = holding['ticker']
        shares = float(holding['shares'])
        avg_price = float(holding['avg_buy_price'])
        total_invested = float(holding['total_invested'])
        total_invested_sum += total_invested

        reserved_shares = get_user_reserved_shares(user_id, ticker)
        available_shares = max(0.0, round(shares - reserved_shares, 6))

        current_price = get_current_price(ticker)
        if current_price and current_price > 0:
            market_value = round(shares * current_price, 2)
            pnl = round(market_value - total_invested, 2)
            pnl_percent = round((pnl / total_invested * 100), 2) if total_invested > 0 else 0.0
            price_available = True
        else:
            current_price = None
            market_value = None
            pnl = None
            pnl_percent = None
            price_available = False

        summary.append({
            "ticker": ticker,
            "shares": shares,
            "reserved_shares": reserved_shares,
            "available_shares": available_shares,
            "avg_price": avg_price,
            "current_price": current_price,
            "total_invested": total_invested,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "price_available": price_available
        })

    all_prices_available = all(h["price_available"] for h in summary)
    known_market_value = round(sum(h["market_value"] for h in summary if h["price_available"]), 2)
    known_pnl = round(sum(h["pnl"] for h in summary if h["price_available"]), 2)

    total_market_value = known_market_value if all_prices_available else None
    total_pnl = known_pnl if all_prices_available else None

    # Compute available cash, buying power, and pending reservations
    try:
        cash_balance = float(get_user_balance(user_id) or 0.0)
        buying_power = float(get_user_buying_power(user_id) or 0.0)
        reserved_cash = float(get_user_reserved_cash(user_id) or 0.0)
        closed_trades = get_closed_trades(user_id)
        realized_pnl = round(sum(float(t.get('pnl', 0.0)) for t in closed_trades), 2)
    except Exception:
        cash_balance = 0.0
        buying_power = 0.0
        reserved_cash = 0.0
        realized_pnl = 0.0

    total_equity = round(cash_balance + known_market_value, 2) if all_prices_available else None

    return {
        "holdings": summary,
        "total_invested": round(total_invested_sum, 2),
        "total_market_value": total_market_value,
        "total_pnl": total_pnl,
        "known_market_value": known_market_value,
        "known_pnl": known_pnl,
        "all_prices_available": all_prices_available,
        "cash_balance": cash_balance,
        "buying_power": buying_power,
        "reserved_cash": reserved_cash,
        "total_equity": total_equity,
        "realized_pnl": realized_pnl
    }


def match_pending_orders(symbol: str = None):
    """
    Evaluates all OPEN limit orders against verified current market prices.
    Executes trades only when price conditions are met:
    - BUY Limit: market_price <= limit_price
    - SELL Limit: market_price >= limit_price

    Price integrity guarantees:
    - Uses get_current_price() abstraction.
    - If market price is unavailable (<= 0), execution is deferred. Never fabricates prices.
    - If cash/shares are insufficient at execution time, order is rejected.
    - Uses fill_order_atomic() for atomic execution and WAC ledger integrity.
    - Prevents double fills via atomic status checks.
    """
    from database import get_open_orders, fill_order_atomic, expire_stale_orders

    try:
        expire_stale_orders()
    except Exception:
        pass

    open_orders = get_open_orders(symbol=symbol)
    fills = []

    for order in open_orders:
        order_id = order['id']
        sym = order['symbol']
        side = order['side'].upper()
        order_type = order['order_type'].upper()
        limit_price = float(order['price']) if order['price'] is not None else 0.0

        if order_type != 'LIMIT':
            continue

        if limit_price <= 0:
            continue

        current_price = get_current_price(sym)
        if current_price <= 0:
            # Missing or invalid market data; defer execution without fabricating prices
            continue

        should_fill = False
        if side == 'BUY' and current_price <= limit_price:
            should_fill = True
        elif side == 'SELL' and current_price >= limit_price:
            should_fill = True

        if should_fill:
            res = fill_order_atomic(order_id=order_id, execution_price=current_price)
            if res.get("success"):
                fills.append(res)

    return fills


def match_single_order(order_id: int):
    """
    Evaluates and attempts immediate execution of a single open order against current market price.
    Returns: Dict containing execution result or failure reason.
    """
    from database import get_connection, fill_order_atomic

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        if not order or order['status'] != 'OPEN':
            return {"success": False, "message": "Order is not OPEN."}

        sym = order['symbol']
        side = order['side'].upper()
        order_type = order['order_type'].upper()
        limit_price = float(order['price']) if order['price'] is not None else 0.0

        current_price = get_current_price(sym)
        if current_price <= 0:
            return {"success": False, "message": f"Could not obtain valid market price for {sym}."}

        should_fill = False
        if order_type == 'MARKET':
            should_fill = True
        elif order_type == 'LIMIT':
            if limit_price <= 0:
                return {"success": False, "message": "Limit price must be greater than zero."}
            if side == 'BUY' and current_price <= limit_price:
                should_fill = True
            elif side == 'SELL' and current_price >= limit_price:
                should_fill = True

        if not should_fill:
            return {
                "success": False,
                "message": f"Price condition not met. Market price: ${current_price:,.2f}, Limit: ${limit_price:,.2f}"
            }

        return fill_order_atomic(order_id=order_id, execution_price=current_price)
    finally:
        conn.close()


def process_ioc_order(order_id: int):
    """
    Executes immediate-or-cancel (IOC) semantics:
    1. Immediately attempts execution against live market price.
    2. If condition is met, order is filled atomically.
    3. If execution cannot proceed or condition is not met, immediately cancels the order,
       instantly releasing reserved buying power or reserved shares.
    4. Since partial fills are not supported by the order book, the entire unfilled quantity is cancelled.
    Returns: Dict summarizing outcome and final order status.
    """
    from database import cancel_order, get_connection

    match_res = match_single_order(order_id)
    if match_res.get("success"):
        return {
            "status": "FILLED",
            "filled": True,
            "order_id": order_id,
            "data": match_res
        }

    # Cancel unfilled order immediately to release reservations
    cancelled = cancel_order(order_id)
    return {
        "status": "CANCELLED",
        "filled": False,
        "order_id": order_id,
        "reason": match_res.get("message", "IOC condition not satisfied immediately.")
    }
