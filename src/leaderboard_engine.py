from datetime import datetime, timedelta, timezone
import database
from analytics_engine import calculate_portfolio_performance

def get_global_leaderboard(period='all_time', limit=100):
    """
    Get leaderboard of top traders
    period: 'weekly', 'monthly', 'all_time'
    """
    
    # In a real app, we'd filter transactions by date for weekly/monthly.
    # For this implementation, we use current P&L as the baseline.
    
    leaderboard = []
    users = database.get_all_users()
    
    for user in users:
        if not user.get('is_public', 1):
            continue
            
        try:
            # Reusing the existing analytics engine
            metrics = calculate_portfolio_performance(user['id'])
            
            leaderboard.append({
                'user_id': user['id'],
                'username': user['username'],
                'avatar_url': user.get('avatar_url'),
                'total_return_pct': metrics['total_pnl_pct'],
                'total_trades': metrics['total_trades'],
                'win_rate': metrics['win_rate'],
                'portfolio_value': metrics['total_value'],
                'sharpe_ratio': metrics['sharpe_ratio']
            })
        except Exception as e:
            print(f"Error calculating leaderboard for user {user['id']}: {e}")
            
    # Sort by return percentage
    leaderboard.sort(key=lambda x: x['total_return_pct'], reverse=True)
    
    # Add ranks
    for i, trader in enumerate(leaderboard[:limit]):
        trader['rank'] = i + 1
        
    return leaderboard[:limit]

def get_user_rank(user_id, period='all_time'):
    """Get a specific user's rank"""
    leaderboard = get_global_leaderboard(period, limit=10000)
    for trader in leaderboard:
        if trader['user_id'] == user_id:
            return trader['rank']
    return None

def get_social_feed(limit=50):
    """Get recent shared trades with user details"""
    return get_shared_trades_feed(limit)
