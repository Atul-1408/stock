import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import database
from trading_engine import get_current_price

def get_historical_price(ticker: str, date: datetime) -> float:
    """Get the closing price for a ticker on a specific historical date."""
    try:
        # Use a small window around the date since markets might be closed
        start = date.strftime('%Y-%m-%d')
        end = (date + timedelta(days=3)).strftime('%Y-%m-%d')
        stock = yf.Ticker(ticker.upper())
        df = stock.history(start=start, end=end)
        if df is None or df.empty:
            return 0.0
        return float(df['Close'].iloc[0])
    except Exception as e:
        print(f"Error fetching historical price for {ticker}: {e}")
        return 0.0

def calculate_portfolio_performance(user_id):
    """Calculate comprehensive portfolio metrics."""
    transactions = database.get_transactions_by_user(user_id, limit=9999)
    portfolio = database.get_user_portfolio(user_id)
    
    # Calculate current total value
    total_value = 0
    for holding in portfolio:
        current_price = get_current_price(holding['ticker'])
        total_value += holding['shares'] * current_price
    
    # Total Invested (from Buy transactions)
    total_invested = sum([t['total_value'] for t in transactions if t['action'] == 'BUY'])
    
    # P&L
    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    
    # Win Rate from closed trades
    closed_trades = database.get_closed_trades(user_id)
    winning_trades = len([t for t in closed_trades if t['pnl'] > 0])
    losing_trades = len([t for t in closed_trades if t['pnl'] <= 0])
    total_trades = len(closed_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    if closed_trades:
        # Use get() with default 0.0 to avoid KeyError if pnl_pct is missing (though it shouldn't be)
        best_trade = max(closed_trades, key=lambda x: x.get('pnl_pct', 0.0))
        worst_trade = min(closed_trades, key=lambda x: x.get('pnl_pct', 0.0))
    else:
        best_trade = worst_trade = None
    
    # Risk Metrics
    daily_returns = calculate_daily_returns(user_id)
    sharpe_ratio = 0
    volatility = 0
    if len(daily_returns) > 1:
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        volatility = daily_returns.std() * np.sqrt(252)
    
    max_drawdown = calculate_max_drawdown(user_id)
    
    return {
        'total_value': round(total_value, 2),
        'total_invested': round(total_invested, 2),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl_pct, 2),
        'win_rate': round(win_rate, 2),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'best_trade': best_trade,
        'worst_trade': worst_trade,
        'sharpe_ratio': round(sharpe_ratio, 2),
        'volatility': round(volatility * 100, 2),
        'max_drawdown': round(max_drawdown * 100, 2)
    }

def get_portfolio_history(user_id, days=30):
    """Get daily portfolio value for charting."""
    transactions = database.get_transactions_by_user(user_id, limit=9999)
    if not transactions:
        return {'dates': [], 'values': [], 'benchmark_values': []}
    
    transactions.sort(key=lambda x: x['timestamp'])
    start_date = datetime.fromisoformat(transactions[0]['timestamp'].replace('Z', '+00:00')).date()
    end_date = datetime.now().date()
    
    dates = []
    values = []
    
    current_date = start_date
    while current_date <= end_date:
        p_value = calculate_portfolio_value_on_date(user_id, current_date)
        dates.append(current_date.isoformat())
        values.append(p_value)
        current_date += timedelta(days=1)
    
    benchmark_values = get_benchmark_performance(start_date, end_date, values[0])
    
    # If benchmark is shorter, pad it
    if len(benchmark_values) < len(values):
        padding = [benchmark_values[-1]] * (len(values) - len(benchmark_values))
        benchmark_values.extend(padding)
    elif len(benchmark_values) > len(values):
        benchmark_values = benchmark_values[:len(values)]

    return {
        'dates': dates,
        'values': values,
        'benchmark_values': benchmark_values
    }

def calculate_portfolio_value_on_date(user_id, date):
    """Reconstruct portfolio value for a specific date."""
    transactions = database.get_transactions_before_date(user_id, date)
    holdings = {}
    cash = database.get_starting_balance(user_id)
    
    for tx in transactions:
        ticker = tx['ticker']
        if tx['action'] == 'BUY':
            holdings[ticker] = holdings.get(ticker, 0) + tx['shares']
            cash -= tx['total_value']
        elif tx['action'] == 'SELL':
            holdings[ticker] = holdings.get(ticker, 0) - tx['shares']
            cash += tx['total_value']
            if holdings[ticker] <= 0: del holdings[ticker]
            
    p_value = cash
    for ticker, shares in holdings.items():
        price = get_historical_price(ticker, date)
        p_value += shares * price
    return p_value

def get_benchmark_performance(start_date, end_date, starting_value):
    """S&P 500 comparison."""
    try:
        spy = yf.Ticker("SPY")
        data = spy.history(start=start_date, end=end_date + timedelta(days=1))
        if data.empty: return [starting_value]
        start_price = data['Close'].iloc[0]
        return (data['Close'] / start_price * starting_value).tolist()
    except:
        return [starting_value]

def calculate_daily_returns(user_id):
    """Daily returns for Sharpe."""
    history = get_portfolio_history(user_id)
    values = history['values']
    if len(values) < 2: return np.array([])
    returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
    return np.array(returns)

def calculate_max_drawdown(user_id):
    """Max peak-to-trough decline."""
    history = get_portfolio_history(user_id)
    values = history['values']
    if len(values) < 2: return 0
    peak = values[0]
    max_dd = 0
    for v in values:
        if v > peak: peak = v
        dd = (peak - v) / peak
        if dd > max_dd: max_dd = dd
    return max_dd

def get_sector_allocation(user_id):
    """Stock allocation by sector."""
    portfolio = database.get_user_portfolio(user_id)
    sectors = {}
    total_val = 0
    for h in portfolio:
        price = get_current_price(h['ticker'])
        val = h['shares'] * price
        total_val += val
        sector = get_stock_sector(h['ticker'])
        sectors[sector] = sectors.get(sector, 0) + val
        
    return {
        'sectors': list(sectors.keys()),
        'values': [round(v, 2) for v in sectors.values()],
        'percentages': [round(v/total_val*100, 2) if total_val > 0 else 0 for v in sectors.values()]
    }

def get_stock_sector(ticker):
    """Fetch sector info via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        return stock.info.get('sector', 'Other')
    except: return 'Other'

def get_risk_metrics(user_id):
    """Calculates Beta, Alpha, R-Squared."""
    p_returns = calculate_daily_returns(user_id)
    m_returns = get_market_returns(len(p_returns))
    
    if len(p_returns) < 5 or len(m_returns) < 5:
        return {'beta': 0, 'alpha': 0, 'r_squared': 0, 'sortino_ratio': 0}
        
    # Standard Beta = Cov(Rp, Rm) / Var(Rm)
    covariance = np.cov(p_returns, m_returns)[0][1]
    m_variance = np.var(m_returns)
    beta = covariance / m_variance if m_variance > 0 else 1
    
    # Alpha = Rp - [Rf + Beta * (Rm - Rf)]
    rf_rate = 0.04 / 252 # 4% annual assumption
    alpha = p_returns.mean() - (rf_rate + beta * (m_returns.mean() - rf_rate))
    
    # R-Squared
    correlation = np.corrcoef(p_returns, m_returns)[0][1]
    r_squared = correlation ** 2
    
    # SortinoRatio
    downside = p_returns[p_returns < 0]
    dd_std = downside.std() if len(downside) > 0 else 0
    sortino = (p_returns.mean() - rf_rate) / dd_std * np.sqrt(252) if dd_std > 0 else 0
    
    return {
        'beta': round(beta, 2),
        'alpha': round(alpha * 252 * 100, 2),
        'r_squared': round(r_squared, 2),
        'sortino_ratio': round(sortino, 2)
    }

def get_market_returns(count):
    """Get SPY returns for benchmark comparison."""
    if count == 0:
        return np.array([])
    spy = yf.Ticker("SPY")
    try:
        data = spy.history(period='1y')  # Get plenty of data
        # yfinance sometimes returns None or raises inside; guard it
        if data is None or data.empty or 'Close' not in data.columns:
            return np.zeros(count)
        returns = data['Close'].pct_change().dropna().values
        if len(returns) >= count:
            return returns[-count:]
        else:
            # pad with zeros so caller doesn’t break
            return np.pad(returns, (count - len(returns), 0))
    except Exception as e:
        print(f"Error fetching market returns: {e}")
        return np.zeros(count)
