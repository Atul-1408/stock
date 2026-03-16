import { useState, useEffect } from 'react';
import axios from 'axios';

function BotWatchlist({ onUpdate }) {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newTicker, setNewTicker] = useState('');
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState('');

  const token = localStorage.getItem('token');
  const config = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const res = await axios.get('/api/bot/watchlist', config);
      setWatchlist(res.data.watchlist);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching watchlist:', error);
      setLoading(false);
    }
  };

  const handleAddTicker = async (e) => {
    e.preventDefault();
    if (!newTicker.trim()) return;

    setAdding(true);
    try {
      await axios.post('/api/bot/watchlist', { ticker: newTicker.toUpperCase() }, config);
      setMessage(`✅ Added ${newTicker} to watchlist!`);
      setNewTicker('');
      fetchWatchlist();
      onUpdate?.();
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('❌ Error adding ticker. Already in watchlist?');
      setTimeout(() => setMessage(''), 3000);
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveTicker = async (ticker) => {
    try {
      await axios.delete(`/api/bot/watchlist/${ticker}`, config);
      setMessage(`✅ Removed ${ticker} from watchlist!`);
      fetchWatchlist();
      onUpdate?.();
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('❌ Error removing ticker');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  if (loading) return <div className="glass-card"><p>Loading watchlist...</p></div>;

  return (
    <div className="glass-card bot-watchlist">
      <h3>👁️ Bot Watchlist</h3>

      {message && <div className="message-banner">{message}</div>}

      {/* Add New Ticker */}
      <form onSubmit={handleAddTicker} className="add-ticker-form">
        <input
          type="text"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
          placeholder="Enter ticker (e.g., AAPL)"
          maxLength="10"
        />
        <button type="submit" className="btn btn-primary" disabled={adding}>
          {adding ? '⏳ Adding...' : '➕ Add to Watchlist'}
        </button>
      </form>

      {/* Watchlist Items */}
      <div className="watchlist-items">
        {watchlist.length > 0 ? (
          <div className="watching-list">
            {watchlist.map(item => (
              <div key={item.id} className="watchlist-item">
                <div className="watchlist-header">
                  <span className="ticker-display">{item.ticker}</span>
                  <button
                    onClick={() => handleRemoveTicker(item.ticker)}
                    className="btn-remove"
                    title="Remove from watchlist"
                  >
                    ❌
                  </button>
                </div>
                <small className="added-date">
                  Added: {new Date(item.added_at).toLocaleDateString()}
                </small>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">No tickers in watchlist. Add some to get started!</p>
        )}
      </div>

      <div className="watchlist-tips">
        <p>💡 Tip: The bot will analyze all tickers in this list for trading signals.</p>
      </div>
    </div>
  );
}

export default BotWatchlist;
