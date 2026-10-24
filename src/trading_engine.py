import yfinance as yf
from database import (
    get_user_balance,
    update_user_balance,
    get_user_shares,
    get_user_portfolio,
    update_portfolio_item,
    delete_portfolio_item,
    add_transaction
)

def get_current_price(ticker: str) -> float:
    """Get the latest closing price using yfinance."""
    try:
        stock = yf.Ticker(ticker.upper())
        data = stock.history(period='1d')
        if not data.empty:
            return float(data['Close'].iloc[-1])
        return 0.0
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return 0.0

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

    price = get_current_price(ticker)
    if price <= 0:
        return {"success": False, "message": f"Could not fetch current price for {ticker}."}

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
    """Fetch user portfolio with live P&L calculation."""
    portfolio = get_user_portfolio(user_id)
    summary = []
    total_market_value = 0
    total_pnl = 0
    
    for holding in portfolio:
        ticker = holding['ticker']
        shares = holding['shares']
        avg_price = holding['avg_buy_price']
        total_invested = holding['total_invested']
        
        current_price = get_current_price(ticker)
        market_value = shares * current_price
        pnl = market_value - total_invested
        pnl_percent = (pnl / total_invested * 100) if total_invested > 0 else 0
        
        summary.append({
            "ticker": ticker,
            "shares": shares,
            "avg_price": avg_price,
            "current_price": current_price,
            "total_invested": total_invested,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent
        })
        
        total_market_value += market_value
        total_pnl += pnl
        
    return {
        "holdings": summary,
        "total_market_value": total_market_value,
        "total_pnl": total_pnl
    }
