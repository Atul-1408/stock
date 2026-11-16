import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import database
import trading_engine

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

def _compute_trade_stats(trades):
    """Calculates win rate, profit factor, average profit/loss for a list of closed trades."""
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'breakeven_trades': 0,
            'win_rate': None,
            'total_pnl': 0.0,
            'avg_profit': None,
            'avg_loss': None,
            'profit_factor': None,
            'closed_cost_basis': 0.0,
            'realized_return_pct': None
        }

    total_trades = len(trades)
    winning_trades = len([t for t in trades if float(t.get('pnl', 0.0) or 0.0) > 0])
    losing_trades = len([t for t in trades if float(t.get('pnl', 0.0) or 0.0) < 0])
    breakeven_trades = len([t for t in trades if float(t.get('pnl', 0.0) or 0.0) == 0])

    win_rate = round((winning_trades / total_trades * 100), 2) if total_trades > 0 else None
    total_pnl = round(sum(float(t.get('pnl', 0.0) or 0.0) for t in trades), 2)

    profits = [float(t.get('pnl', 0.0) or 0.0) for t in trades if float(t.get('pnl', 0.0) or 0.0) > 0]
    losses = [float(t.get('pnl', 0.0) or 0.0) for t in trades if float(t.get('pnl', 0.0) or 0.0) < 0]

    avg_profit = round(sum(profits) / len(profits), 2) if profits else None
    avg_loss = round(sum(losses) / len(losses), 2) if losses else None

    abs_losses = abs(sum(losses))
    if abs_losses > 0:
        profit_factor = round(sum(profits) / abs_losses, 2)
    elif profits:
        profit_factor = float('inf')
    else:
        profit_factor = None

    closed_cost_basis = round(sum(float(t.get('cost_basis', 0.0) or 0.0) for t in trades), 2)
    realized_return_pct = round((total_pnl / closed_cost_basis * 100), 2) if closed_cost_basis > 0 else None

    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'breakeven_trades': breakeven_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'closed_cost_basis': closed_cost_basis,
        'realized_return_pct': realized_return_pct
    }


def calculate_portfolio_performance(user_id):
    """Calculate comprehensive portfolio metrics using WAC basis, realized P&L, and bot/manual separation."""
    portfolio = database.get_user_portfolio(user_id)
    
    # 1. Holdings valuation and price integrity
    active_invested = 0.0
    known_market_value = 0.0
    known_unrealized_pnl = 0.0
    unpriced_tickers = []

    for holding in portfolio:
        ticker = holding['ticker']
        shares = float(holding.get('shares', 0) or 0)
        invested = float(holding.get('total_invested', 0) or 0)
        active_invested += invested

        current_price = trading_engine.get_current_price(ticker)
        if current_price and current_price > 0:
            mv = shares * current_price
            known_market_value += mv
            known_unrealized_pnl += (mv - invested)
        else:
            unpriced_tickers.append(ticker)

    all_prices_available = (len(unpriced_tickers) == 0)
    total_value = round(known_market_value, 2) if all_prices_available else None
    unrealized_pnl = round(known_unrealized_pnl, 2) if all_prices_available else None

    # 2. Realized P&L from closed trades
    closed_trades = database.get_closed_trades(user_id)
    overall_stats = _compute_trade_stats(closed_trades)
    realized_pnl = overall_stats['total_pnl']
    closed_cost_basis = overall_stats['closed_cost_basis']

    # Separate bot vs manual performance
    bot_closed_trades = [t for t in closed_trades if t.get('is_bot') == 1]
    manual_closed_trades = [t for t in closed_trades if t.get('is_bot') == 0]
    unattributed_trades = [t for t in closed_trades if t.get('is_bot') is None]

    bot_stats = _compute_trade_stats(bot_closed_trades)
    manual_stats = _compute_trade_stats(manual_closed_trades)
    unattributed_stats = _compute_trade_stats(unattributed_trades)

    # 3. Total Combined P&L
    if unrealized_pnl is not None:
        total_pnl = round(realized_pnl + unrealized_pnl, 2)
    else:
        total_pnl = None

    # 4. Cash Balances and Buying Power
    cash_balance = float(database.get_user_balance(user_id) or 0.0)
    reserved_cash = float(database.get_user_reserved_cash(user_id) or 0.0)
    buying_power = float(database.get_user_buying_power(user_id) or 0.0)
    starting_balance = float(database.get_starting_balance(user_id) or 0.0)
    portfolio_equity = round(cash_balance + known_market_value, 2) if all_prices_available else None

    # 5. Returns with explicitly documented denominators
    # Unrealized return on active open capital
    unrealized_return_pct = (
        round((unrealized_pnl / active_invested * 100), 2)
        if (active_invested > 0 and unrealized_pnl is not None)
        else None
    )
    # Realized return on closed capital basis
    realized_return_pct = overall_stats['realized_return_pct']
    
    # Return on starting deposit
    return_on_starting_capital_pct = (
        round((total_pnl / starting_balance * 100), 2)
        if (starting_balance > 0 and total_pnl is not None)
        else None
    )
    
    # Backwards-compatible total_pnl_pct
    total_pnl_pct = return_on_starting_capital_pct if return_on_starting_capital_pct is not None else 0.0

    # Best / Worst Trade
    if closed_trades:
        best_trade = max(closed_trades, key=lambda x: float(x.get('pnl', 0.0) or 0.0))
        worst_trade = min(closed_trades, key=lambda x: float(x.get('pnl', 0.0) or 0.0))
    else:
        best_trade = worst_trade = None

    # 6. Risk metrics safely guarded
    sharpe_ratio = 0.0
    volatility = 0.0
    try:
        daily_returns = calculate_daily_returns(user_id)
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe_ratio = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))
            volatility = float(daily_returns.std() * np.sqrt(252))
    except Exception:
        pass

    max_drawdown = 0.0
    try:
        max_drawdown = float(calculate_max_drawdown(user_id))
    except Exception:
        pass

    return {
        'total_value': total_value,
        'known_market_value': round(known_market_value, 2),
        'total_invested': round(active_invested, 2),
        'cash_balance': round(cash_balance, 2),
        'reserved_cash': round(reserved_cash, 2),
        'buying_power': round(buying_power, 2),
        'starting_balance': round(starting_balance, 2),
        'portfolio_equity': portfolio_equity,
        'realized_pnl': round(realized_pnl, 2),
        'unrealized_pnl': unrealized_pnl,
        'known_unrealized_pnl': round(known_unrealized_pnl, 2),
        'total_pnl': total_pnl,
        'total_pnl_pct': round(total_pnl_pct, 2),
        'unrealized_return_pct': unrealized_return_pct,
        'realized_return_pct': realized_return_pct,
        'return_on_starting_capital_pct': return_on_starting_capital_pct,
        'all_prices_available': all_prices_available,
        'unpriced_tickers': unpriced_tickers,
        'win_rate': overall_stats['win_rate'] if overall_stats['win_rate'] is not None else 0.0,
        'win_rate_raw': overall_stats['win_rate'],
        'total_trades': overall_stats['total_trades'],
        'winning_trades': overall_stats['winning_trades'],
        'losing_trades': overall_stats['losing_trades'],
        'breakeven_trades': overall_stats['breakeven_trades'],
        'avg_profit': overall_stats['avg_profit'] if overall_stats['avg_profit'] is not None else 0.0,
        'avg_loss': overall_stats['avg_loss'] if overall_stats['avg_loss'] is not None else 0.0,
        'profit_factor': overall_stats['profit_factor'],
        'best_trade': best_trade,
        'worst_trade': worst_trade,
        'bot_performance': bot_stats,
        'manual_performance': manual_stats,
        'unattributed_performance': unattributed_stats,
        'sharpe_ratio': round(sharpe_ratio, 2) if sharpe_ratio else 0.0,
        'volatility': round(volatility * 100, 2) if volatility else 0.0,
        'max_drawdown': round(max_drawdown * 100, 2) if max_drawdown else 0.0
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
        if price <= 0:
            price = trading_engine.get_current_price(ticker)
        if price and price > 0:
            p_value += shares * price
    return round(p_value, 2)

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
        price = trading_engine.get_current_price(h['ticker'])
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
