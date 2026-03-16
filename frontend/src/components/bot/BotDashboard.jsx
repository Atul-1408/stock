import { useState, useEffect } from 'react';
import axios from 'axios';
import BotSettings from './BotSettings';
import BotWatchlist from './BotWatchlist';
import BotSignals from './BotSignals';
import BotTrades from './BotTrades';
import './BotDashboard.css';

function BotDashboard() {
  const [status, setStatus] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState(null);

  const token = localStorage.getItem('token');
  const config = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchBotData();

    // Refresh every 30 seconds
    const interval = setInterval(fetchBotData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchBotData = async () => {
    try {
      setError(null);
      const [statusRes, perfRes] = await Promise.all([
        axios.get('/api/bot/status', config),
        axios.get('/api/bot/performance', config)
      ]);

      setStatus(statusRes.data);
      setPerformance(perfRes.data);
    } catch (error) {
      console.error('Error fetching bot data:', error);
      setError('Failed to load bot data');
    } finally {
      setLoading(false);
    }
  };

  const toggleBot = async () => {
    try {
      if (status.is_active) {
        await axios.post('/api/bot/stop', {}, config);
      } else {
        await axios.post('/api/bot/start', {}, config);
      }

      fetchBotData();
    } catch (error) {
      setError('Failed to toggle bot');
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading bot dashboard...</p>
      </div>
    );
  }

  return (
    <div className="bot-dashboard">
      {error && <div className="error-banner">{error}</div>}

      {/* Header */}
      <div className="bot-header glass-card animate-fade-in-up">
        <div className="bot-title-section">
          <h1>🤖 Trading Bot</h1>
          <p className="bot-subtitle">
            {status?.config?.bot_name || 'My Trading Bot'}
          </p>
        </div>

        <div className="bot-controls">
          <div className={`bot-status-badge ${status?.is_active ? 'active' : 'inactive'}`}>
            {status?.is_active ? '🟢 Active' : '🔴 Inactive'}
          </div>

          <button
            onClick={toggleBot}
            className={`btn ${status?.is_active ? 'btn-danger' : 'btn-primary'}`}
          >
            {status?.is_active ? '⏸️ Stop Bot' : '▶️ Start Bot'}
          </button>
        </div>
      </div>

      {/* Performance Stats */}
      <div className="grid grid-4" style={{ marginTop: '24px' }}>
        <div className="stat-card animate-fade-in-up stagger-1">
          <div className="stat-icon">📊</div>
          <div className="stat-label">Total Trades</div>
          <div className="stat-value">{performance?.total_trades || 0}</div>
          <div className="stat-change neutral">
            {performance?.winning_trades || 0}W / {performance?.losing_trades || 0}L
          </div>
        </div>

        <div className="stat-card animate-fade-in-up stagger-2">
          <div className="stat-icon">🎯</div>
          <div className="stat-label">Win Rate</div>
          <div className="stat-value">{performance?.win_rate || 0}%</div>
          <div className={`stat-change ${performance?.win_rate >= 50 ? 'positive' : 'negative'}`}>
            {performance?.win_rate >= 50 ? '↗' : '↘'} Target: 60%
          </div>
        </div>

        <div className="stat-card animate-fade-in-up stagger-3">
          <div className="stat-icon">💰</div>
          <div className="stat-label">Total P&L</div>
          <div className="stat-value">
            ${(performance?.total_pnl || 0).toLocaleString()}
          </div>
          <div className={`stat-change ${performance?.total_pnl >= 0 ? 'positive' : 'negative'}`}>
            {performance?.total_pnl >= 0 ? '↗' : '↘'}
            {performance?.total_pnl >= 0 ? '+' : ''}{performance?.total_pnl || 0}
          </div>
        </div>

        <div className="stat-card animate-fade-in-up stagger-4">
          <div className="stat-icon">📈</div>
          <div className="stat-label">Avg Profit</div>
          <div className="stat-value">
            ${Math.abs(performance?.avg_profit || 0).toFixed(2)}
          </div>
          <div className="stat-change positive">
            Loss: ${Math.abs(performance?.avg_loss || 0).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bot-tabs glass-card" style={{ marginTop: '24px' }}>
        <button
          className={`bot-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📊 Overview
        </button>
        <button
          className={`bot-tab ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          ⚙️ Settings
        </button>
        <button
          className={`bot-tab ${activeTab === 'watchlist' ? 'active' : ''}`}
          onClick={() => setActiveTab('watchlist')}
        >
          👁️ Watchlist ({status?.watchlist?.length || 0})
        </button>
        <button
          className={`bot-tab ${activeTab === 'signals' ? 'active' : ''}`}
          onClick={() => setActiveTab('signals')}
        >
          🎯 Signals
        </button>
        <button
          className={`bot-tab ${activeTab === 'trades' ? 'active' : ''}`}
          onClick={() => setActiveTab('trades')}
        >
          📈 Trades
        </button>
      </div>

      {/* Tab Content */}
      <div className="bot-content" style={{ marginTop: '24px' }}>
        {activeTab === 'overview' && (
          <div className="grid grid-2">
            {/* Recent Signals */}
            <div className="glass-card">
              <h3>🎯 Recent Signals</h3>
              <div className="signals-list">
                {status?.recent_signals?.length > 0 ? (
                  status.recent_signals.map(signal => (
                    <div key={signal.id} className="signal-item">
                      <div className="signal-header">
                        <span className="ticker-badge">{signal.ticker}</span>
                        <span className={`signal-badge ${signal.signal_type.toLowerCase()}`}>
                          {signal.signal_type}
                        </span>
                      </div>
                      <div className="signal-details">
                        <span>Confidence: {(signal.confidence * 100).toFixed(0)}%</span>
                        <span>Price: ${signal.price?.toFixed(2) || 'N/A'}</span>
                      </div>
                      <p className="signal-reasoning">{signal.reasoning}</p>
                      <span className="signal-time">
                        {new Date(signal.created_at).toLocaleString()}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="empty-state">No signals yet</p>
                )}
              </div>
            </div>

            {/* Open Positions */}
            <div className="glass-card">
              <h3>📊 Open Positions</h3>
              <div className="positions-list">
                {status?.open_positions?.length > 0 ? (
                  status.open_positions.map(position => (
                    <div key={position.id} className="position-item">
                      <div className="position-header">
                        <span className="ticker-badge">{position.ticker}</span>
                        <span className="position-shares">
                          {position.shares} shares
                        </span>
                      </div>
                      <div className="position-prices">
                        <div>
                          <small>Entry</small>
                          <strong>${position.entry_price?.toFixed(2)}</strong>
                        </div>
                        <div>
                          <small>Stop Loss</small>
                          <strong>${position.stop_loss?.toFixed(2) || 'N/A'}</strong>
                        </div>
                        <div>
                          <small>Take Profit</small>
                          <strong>${position.take_profit?.toFixed(2) || 'N/A'}</strong>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="empty-state">No open positions</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && <BotSettings onUpdate={fetchBotData} />}
        {activeTab === 'watchlist' && <BotWatchlist onUpdate={fetchBotData} />}
        {activeTab === 'signals' && <BotSignals />}
        {activeTab === 'trades' && <BotTrades />}
      </div>
    </div>
  );
}

export default BotDashboard;
