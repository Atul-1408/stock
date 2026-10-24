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
    Executes a paper trade with balance and portfolio validation.
    Returns: {'success': bool, 'data': dict, 'message': str}
    """
    ticker = ticker.upper()
    action = action.upper()
    
    if shares <= 0:
        return {"success": False, "message": "Shares must be greater than zero."}

    price = get_current_price(ticker)
    if price <= 0:
        return {"success": False, "message": f"Could not fetch current price for {ticker}."}

    total_value = shares * price
    current_balance = get_user_balance(user_id)

    if action == 'BUY':
        if current_balance < total_value:
            return {"success": False, "message": "Insufficient balance for this trade."}
        
        # Update Balance
        new_balance = current_balance - total_value
        update_user_balance(user_id, new_balance)
        
        # Update Portfolio
        existing_shares = get_user_shares(user_id, ticker)
        portfolio = get_user_portfolio(user_id)
        
        # Find existing holding to update average price
        avg_price = price
        total_invested = total_value
        
        for holding in portfolio:
            if holding['ticker'] == ticker:
                avg_price = (holding['total_invested'] + total_value) / (holding['shares'] + shares)
                total_invested = holding['total_invested'] + total_value
                break
        
        update_portfolio_item(user_id, ticker, existing_shares + shares, avg_price, total_invested)
        
    elif action == 'SELL':
        existing_shares = get_user_shares(user_id, ticker)
        if existing_shares < shares:
            return {"success": False, "message": f"Insufficient shares. You only own {existing_shares} shares of {ticker}."}
        
        # Update Balance
        new_balance = current_balance + total_value
        update_user_balance(user_id, new_balance)
        
        # Update Portfolio
        new_shares = existing_shares - shares
        if new_shares == 0:
            delete_portfolio_item(user_id, ticker)
        else:
            # When selling, average buy price stays the same, but total invested decreases proportionally
            portfolio = get_user_portfolio(user_id)
            avg_price = price # default fallback
            total_invested = 0
            for holding in portfolio:
                if holding['ticker'] == ticker:
                    avg_price = holding['avg_buy_price']
                    total_invested = holding['total_invested'] - (shares * avg_price)
                    break
            update_portfolio_item(user_id, ticker, new_shares, avg_price, total_invested)

    else:
        return {"success": False, "message": "Invalid action. Use BUY or SELL."}

    # Log Transaction
    add_transaction(user_id, ticker, action, shares, price, total_value, sentiment_score, sentiment_label)
    
    # Return updated portfolio and balance to prevent race conditions on the frontend
    updated_portfolio = get_portfolio_summary(user_id)
    final_balance = get_user_balance(user_id)

    return {
        "success": True, 
        "message": f"Successfully {action.lower()}ed {shares} shares of {ticker}.",
        "data": {
            "portfolio": updated_portfolio,
            "balance": final_balance
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
