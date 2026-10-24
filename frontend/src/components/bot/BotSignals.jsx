import { useState, useEffect } from 'react';
import axios from 'axios';

function BotSignals() {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  const token = localStorage.getItem('token');
  const config = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchSignals = async () => {
    try {
      const res = await axios.get('/api/bot/signals?limit=50', config);
      setSignals(res.data.signals);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching signals:', error);
      setLoading(false);
    }
  };

  const filteredSignals = filter === 'all'
    ? signals
    : signals.filter(s => s.signal_type.toUpperCase() === filter.toUpperCase());

  const buyCount = signals.filter(s => s.signal_type === 'BUY').length;
  const sellCount = signals.filter(s => s.signal_type === 'SELL').length;

  if (loading) return <div className="glass-card"><p>Loading signals...</p></div>;

  return (
    <div className="glass-card bot-signals">
      <h3>🎯 Bot Signals</h3>

      {/* Signal Stats */}
      <div className="signal-stats">
        <div className="stat">
          <span className="label">Buy Signals</span>
          <span className="value buy">{buyCount}</span>
        </div>
        <div className="stat">
          <span className="label">Sell Signals</span>
          <span className="value sell">{sellCount}</span>
        </div>
        <div className="stat">
          <span className="label">Total</span>
          <span className="value">{signals.length}</span>
        </div>
      </div>

      {/* Filter */}
      <div className="signal-filter">
        <button
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All ({signals.length})
        </button>
        <button
          className={`filter-btn ${filter === 'buy' ? 'active' : ''}`}
          onClick={() => setFilter('buy')}
        >
          Buy ({buyCount})
        </button>
        <button
          className={`filter-btn ${filter === 'sell' ? 'active' : ''}`}
          onClick={() => setFilter('sell')}
        >
          Sell ({sellCount})
        </button>
      </div>

      {/* Signals List */}
      <div className="signals-container">
        {filteredSignals.length > 0 ? (
          filteredSignals.map(signal => (
            <div key={signal.id} className={`signal-card ${signal.signal_type.toLowerCase()}`}>
              <div className="signal-top">
                <div className="ticker-info">
                  <span className="ticker">{signal.ticker}</span>
                  <span className={`signal-badge ${signal.signal_type.toLowerCase()}`}>
                    {signal.signal_type}
                  </span>
                </div>
                <div className="confidence">
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{ width: `${(signal.confidence || 0) * 100}%` }}
                    ></div>
                  </div>
                  <span className="confidence-text">
                    {((signal.confidence || 0) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              <div className="signal-middle">
                <div className="score-item">
                  <span className="score-label">Price</span>
                  <span className="score-value">${signal.price?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="score-item">
                  <span className="score-label">Sentiment</span>
                  <span className="score-value senti">{signal.sentiment_score?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="score-item">
                  <span className="score-label">Technical</span>
                  <span className="score-value tech">{signal.technical_score?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="score-item">
                  <span className="score-label">ML</span>
                  <span className="score-value ml">{signal.ml_score?.toFixed(2) || 'N/A'}</span>
                </div>
              </div>

              <div className="signal-reasoning">
                <p>{signal.reasoning}</p>
              </div>

              <div className="signal-status">
                <span className={`status-badge ${signal.was_executed ? 'executed' : 'pending'}`}>
                  {signal.was_executed ? '✅ Executed' : '⏳ Pending'}
                </span>
                <span className="signal-time">
                  {new Date(signal.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))
        ) : (
          <p className="empty-state">No signals generated yet. Check back soon!</p>
        )}
      </div>
    </div>
  );
}

export default BotSignals;
