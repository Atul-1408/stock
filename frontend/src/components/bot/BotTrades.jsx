import { useState, useEffect } from 'react';
import axios from 'axios';

function BotTrades() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  const token = localStorage.getItem('token');
  const config = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchTrades = async () => {
    try {
      const res = await axios.get('/api/bot/trades', config);
      setTrades(res.data.trades);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching trades:', error);
      setLoading(false);
    }
  };

  const filteredTrades = filter === 'all'
    ? trades
    : trades.filter(t => t.status.toUpperCase() === filter.toUpperCase());

  const openCount = trades.filter(t => t.status === 'OPEN').length;
  const closedCount = trades.filter(t => t.status === 'CLOSED').length;

  const calculateStats = () => {
    const closed = trades.filter(t => t.status === 'CLOSED');
    if (closed.length === 0) return { wins: 0, losses: 0, totalPnL: 0, avgWin: 0, avgLoss: 0 };

    const wins = closed.filter(t => t.pnl > 0).length;
    const losses = closed.filter(t => t.pnl < 0).length;
    const totalPnL = closed.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const wins_pnl = closed.filter(t => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0);
    const losses_pnl = closed.filter(t => t.pnl < 0).reduce((sum, t) => sum + t.pnl, 0);

    return {
      wins,
      losses,
      totalPnL,
      avgWin: wins > 0 ? wins_pnl / wins : 0,
      avgLoss: losses > 0 ? losses_pnl / losses : 0
    };
  };

  const stats = calculateStats();

  if (loading) return <div className="glass-card"><p>Loading trades...</p></div>;

  return (
    <div className="glass-card bot-trades">
      <h3>📈 Trade History</h3>

      {/* Trade Stats */}
      <div className="trade-stats">
        <div className="stat">
          <span className="label">Open</span>
          <span className="value">{openCount}</span>
        </div>
        <div className="stat">
          <span className="label">Closed</span>
          <span className="value">{closedCount}</span>
        </div>
        <div className="stat">
          <span className="label">Total P&L</span>
          <span className={`value ${stats.totalPnL >= 0 ? 'positive' : 'negative'}`}>
            ${stats.totalPnL.toFixed(2)}
          </span>
        </div>
        <div className="stat">
          <span className="label">Avg Win</span>
          <span className="value positive">${stats.avgWin.toFixed(2)}</span>
        </div>
        <div className="stat">
          <span className="label">Avg Loss</span>
          <span className="value negative">${stats.avgLoss.toFixed(2)}</span>
        </div>
      </div>

      {/* Filter */}
      <div className="trade-filter">
        <button
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All ({trades.length})
        </button>
        <button
          className={`filter-btn ${filter === 'open' ? 'active' : ''}`}
          onClick={() => setFilter('open')}
        >
          Open ({openCount})
        </button>
        <button
          className={`filter-btn ${filter === 'closed' ? 'active' : ''}`}
          onClick={() => setFilter('closed')}
        >
          Closed ({closedCount})
        </button>
      </div>

      {/* Trades Table */}
      <div className="trades-container">
        {filteredTrades.length > 0 ? (
          <table className="trades-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Action</th>
                <th>Shares</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Stop Loss</th>
                <th>Take Profit</th>
                <th>P&L</th>
                <th>P&L %</th>
                <th>Status</th>
                <th>Entry Time</th>
                <th>Exit Time</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map(trade => (
                <tr key={trade.id} className={`status-${trade.status.toLowerCase()}`}>
                  <td className="ticker">{trade.ticker}</td>
                  <td className={`action ${trade.action.toLowerCase()}`}>{trade.action}</td>
                  <td>{trade.shares}</td>
                  <td>${trade.entry_price?.toFixed(2)}</td>
                  <td>{trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : 'N/A'}</td>
                  <td>${trade.stop_loss?.toFixed(2) || 'N/A'}</td>
                  <td>${trade.take_profit?.toFixed(2) || 'N/A'}</td>
                  <td className={`pnl ${(trade.pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                    ${(trade.pnl || 0).toFixed(2)}
                  </td>
                  <td className={`pnl-pct ${(trade.pnl_pct || 0) >= 0 ? 'positive' : 'negative'}`}>
                    {(trade.pnl_pct || 0) >= 0 ? '+' : ''}{(trade.pnl_pct || 0).toFixed(2)}%
                  </td>
                  <td>
                    <span className={`status-badge ${trade.status.toLowerCase()}`}>
                      {trade.status}
                    </span>
                  </td>
                  <td>{new Date(trade.entry_time).toLocaleString()}</td>
                  <td>{trade.exit_time ? new Date(trade.exit_time).toLocaleString() : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty-state">No trades yet.</p>
        )}
      </div>
    </div>
  );
}

export default BotTrades;
