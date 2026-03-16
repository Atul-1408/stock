import { useState, useEffect } from 'react';
import axios from 'axios';

function BotSettings({ onUpdate }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const token = localStorage.getItem('token');
  const axiosConfig = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await axios.get('/api/bot/config', axiosConfig);
      setConfig(res.data.config);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching config:', error);
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (checked ? 1 : 0) : value
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await axios.put('/api/bot/config', config, axiosConfig);
      setMessage('✅ Settings saved successfully!');
      setTimeout(() => setMessage(''), 3000);
      onUpdate?.();
    } catch (error) {
      setMessage('❌ Error saving settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="glass-card"><p>Loading settings...</p></div>;

  if (!config) return <div className="glass-card"><p>Error loading settings</p></div>;

  return (
    <div className="glass-card bot-settings">
      <h3>⚙️ Bot Configuration</h3>

      {message && <div className="message-banner">{message}</div>}

      <form onSubmit={handleSave} className="settings-form">
        {/* Bot Name */}
        <div className="form-group">
          <label>Bot Name</label>
          <input
            type="text"
            name="bot_name"
            value={config.bot_name || ''}
            onChange={handleChange}
            placeholder="My Trading Bot"
          />
        </div>

        {/* Risk Level */}
        <div className="form-group">
          <label>Risk Level</label>
          <select name="risk_level" value={config.risk_level || 'MEDIUM'} onChange={handleChange}>
            <option value="LOW">Low (Conservative)</option>
            <option value="MEDIUM">Medium (Balanced)</option>
            <option value="HIGH">High (Aggressive)</option>
          </select>
        </div>

        {/* Max Position Size */}
        <div className="form-group">
          <label>Max Position Size ($)</label>
          <input
            type="number"
            name="max_position_size"
            value={config.max_position_size || 10000}
            onChange={handleChange}
            step="100"
          />
        </div>

        {/* Min Sentiment Score */}
        <div className="form-group">
          <label>Min Sentiment Score</label>
          <input
            type="number"
            name="min_sentiment_score"
            value={config.min_sentiment_score || 0.3}
            onChange={handleChange}
            min="0"
            max="1"
            step="0.1"
          />
        </div>

        {/* Stop Loss % */}
        <div className="form-group">
          <label>Stop Loss (%)</label>
          <input
            type="number"
            name="stop_loss_pct"
            value={config.stop_loss_pct || 0.05}
            onChange={handleChange}
            min="0.01"
            max="1"
            step="0.01"
          />
        </div>

        {/* Take Profit % */}
        <div className="form-group">
          <label>Take Profit (%)</label>
          <input
            type="number"
            name="take_profit_pct"
            value={config.take_profit_pct || 0.1}
            onChange={handleChange}
            min="0.01"
            max="1"
            step="0.01"
          />
        </div>

        {/* Max Trades Per Day */}
        <div className="form-group">
          <label>Max Trades Per Day</label>
          <input
            type="number"
            name="max_trades_per_day"
            value={config.max_trades_per_day || 10}
            onChange={handleChange}
            min="1"
            max="100"
          />
        </div>

        {/* Trading Hours Start */}
        <div className="form-group">
          <label>Trading Hours Start</label>
          <input
            type="time"
            name="trading_hours_start"
            value={config.trading_hours_start?.slice(0, 5) || '09:30'}
            onChange={handleChange}
          />
        </div>

        {/* Trading Hours End */}
        <div className="form-group">
          <label>Trading Hours End</label>
          <input
            type="time"
            name="trading_hours_end"
            value={config.trading_hours_end?.slice(0, 5) || '16:00'}
            onChange={handleChange}
          />
        </div>

        {/* Checkboxes for Indicators */}
        <div className="form-group checkbox-group">
          <label>
            <input
              type="checkbox"
              name="use_sentiment"
              checked={config.use_sentiment === 1}
              onChange={handleChange}
            />
            Use Sentiment Analysis
          </label>
          <label>
            <input
              type="checkbox"
              name="use_technical"
              checked={config.use_technical === 1}
              onChange={handleChange}
            />
            Use Technical Indicators
          </label>
          <label>
            <input
              type="checkbox"
              name="use_ml_model"
              checked={config.use_ml_model === 1}
              onChange={handleChange}
            />
            Use ML Predictions
          </label>
        </div>

        {/* Save Button */}
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? '💾 Saving...' : '💾 Save Settings'}
        </button>
      </form>
    </div>
  );
}

export default BotSettings;
