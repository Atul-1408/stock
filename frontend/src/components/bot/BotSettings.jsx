import React, { useState, useEffect } from "react";
import { Sliders, Save, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import api from "../../utils/api";

function BotSettings({ onUpdate }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await api.get("/bot/config");
      setConfig(res.data.config);
    } catch (err) {
      console.error("Error fetching config:", err);
      setError("Unable to load bot strategy configuration.");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setConfig((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? (checked ? 1 : 0) : value
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await api.put("/bot/config", config);
      setMessage("Strategy parameters successfully synchronized.");
      setTimeout(() => setMessage(""), 3500);
      onUpdate?.();
    } catch (err) {
      setError("Failed to persist strategy configuration.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="terminal-card py-12 flex flex-col items-center justify-center gap-3">
        <RefreshCw className="w-5 h-5 text-terminal-cyan animate-spin" />
        <span className="font-mono text-xs text-slate-400">Loading strategy settings...</span>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="terminal-card py-8 text-center font-mono text-xs text-terminal-coral">
        Failed to load bot strategy configuration.
      </div>
    );
  }

  return (
    <div className="terminal-card">
      <div className="flex items-center justify-between border-b border-terminal-800 pb-3 mb-6">
        <div>
          <h2 className="font-mono text-sm uppercase font-bold text-slate-100 tracking-wider flex items-center gap-2">
            <Sliders className="w-4 h-4 text-terminal-cyan" />
            Execution Parameters & Risk Rules
          </h2>
          <p className="font-mono text-2xs text-slate-400 mt-0.5">
            Configure order sizing, threshold triggers, and automated guardrails.
          </p>
        </div>
      </div>

      {message && (
        <div className="mb-4 p-3 rounded border border-terminal-emerald/30 bg-terminal-emerald/10 text-terminal-emerald font-mono text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 rounded border border-terminal-coral/30 bg-terminal-coral/10 text-terminal-coral font-mono text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Bot Name */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Algorithm Identifier
            </label>
            <input
              type="text"
              name="bot_name"
              value={config.bot_name || ""}
              onChange={handleChange}
              placeholder="e.g., Sovereign Alpha V1"
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 focus:outline-none focus:border-terminal-cyan"
            />
          </div>

          {/* Risk Level */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Risk Profile Mode
            </label>
            <select
              name="risk_level"
              value={config.risk_level || "MEDIUM"}
              onChange={handleChange}
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 focus:outline-none focus:border-terminal-cyan"
            >
              <option value="LOW">CONSERVATIVE (Low Volatility)</option>
              <option value="MEDIUM">BALANCED (Moderate Exposure)</option>
              <option value="HIGH">AGGRESSIVE (High Momentum)</option>
            </select>
          </div>

          {/* Max Position Size */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Max Position Sizing ($ USD)
            </label>
            <input
              type="number"
              name="max_position_size"
              value={config.max_position_size || 10000}
              onChange={handleChange}
              step="100"
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 font-num focus:outline-none focus:border-terminal-cyan"
            />
          </div>

          {/* Min Sentiment Score */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Min NLP Sentiment Cutoff (0.0 to 1.0)
            </label>
            <input
              type="number"
              name="min_sentiment_score"
              value={config.min_sentiment_score ?? 0.3}
              onChange={handleChange}
              min="0"
              max="1"
              step="0.05"
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 font-num focus:outline-none focus:border-terminal-cyan"
            />
          </div>

          {/* Stop Loss % */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Hard Stop Loss Ratio (e.g. 0.05 = 5%)
            </label>
            <input
              type="number"
              name="stop_loss_pct"
              value={config.stop_loss_pct ?? 0.05}
              onChange={handleChange}
              min="0.01"
              max="0.5"
              step="0.01"
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 font-num focus:outline-none focus:border-terminal-cyan"
            />
          </div>

          {/* Take Profit % */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Take Profit Target Ratio (e.g. 0.10 = 10%)
            </label>
            <input
              type="number"
              name="take_profit_pct"
              value={config.take_profit_pct ?? 0.1}
              onChange={handleChange}
              min="0.01"
              max="1.0"
              step="0.01"
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 font-num focus:outline-none focus:border-terminal-cyan"
            />
          </div>

          {/* Max Trades Per Day */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Max Daily Executions Cap
            </label>
            <input
              type="number"
              name="max_trades_per_day"
              value={config.max_trades_per_day || 10}
              onChange={handleChange}
              min="1"
              max="100"
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 font-num focus:outline-none focus:border-terminal-cyan"
            />
          </div>

          {/* Trading Hours Start */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Trading Window Open (UTC / EST)
            </label>
            <input
              type="time"
              name="trading_hours_start"
              value={config.trading_hours_start?.slice(0, 5) || "09:30"}
              onChange={handleChange}
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 focus:outline-none focus:border-terminal-cyan"
            />
          </div>

          {/* Trading Hours End */}
          <div>
            <label className="block font-mono text-2xs uppercase tracking-wider text-slate-300 mb-1.5">
              Trading Window Close
            </label>
            <input
              type="time"
              name="trading_hours_end"
              value={config.trading_hours_end?.slice(0, 5) || "16:00"}
              onChange={handleChange}
              className="w-full bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 focus:outline-none focus:border-terminal-cyan"
            />
          </div>
        </div>

        {/* Signals Signal Feeds Toggle Group */}
        <div className="p-4 rounded border border-terminal-800 bg-terminal-950/40 space-y-3">
          <div className="font-mono text-2xs uppercase tracking-wider font-bold text-slate-300">
            Signal Feed Engines
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="flex items-center gap-3 p-2.5 rounded border border-terminal-800 bg-terminal-900 cursor-pointer hover:border-terminal-700 transition-colors">
              <input
                type="checkbox"
                name="use_sentiment"
                checked={config.use_sentiment === 1}
                onChange={handleChange}
                className="w-4 h-4 rounded border-terminal-600 bg-terminal-950 text-terminal-cyan focus:ring-0"
              />
              <span className="font-mono text-xs text-slate-200">Real-time NLP Sentiment</span>
            </label>

            <label className="flex items-center gap-3 p-2.5 rounded border border-terminal-800 bg-terminal-900 cursor-pointer hover:border-terminal-700 transition-colors">
              <input
                type="checkbox"
                name="use_technical"
                checked={config.use_technical === 1}
                onChange={handleChange}
                className="w-4 h-4 rounded border-terminal-600 bg-terminal-950 text-terminal-cyan focus:ring-0"
              />
              <span className="font-mono text-xs text-slate-200">Technical Indicators (RSI/MACD)</span>
            </label>

            <label className="flex items-center gap-3 p-2.5 rounded border border-terminal-800 bg-terminal-900 cursor-pointer hover:border-terminal-700 transition-colors">
              <input
                type="checkbox"
                name="use_ml_model"
                checked={config.use_ml_model === 1}
                onChange={handleChange}
                className="w-4 h-4 rounded border-terminal-600 bg-terminal-950 text-terminal-cyan focus:ring-0"
              />
              <span className="font-mono text-xs text-slate-200">Proprietary ML Model Predictions</span>
            </label>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2.5 rounded bg-terminal-cyan/10 border border-terminal-cyan/40 hover:bg-terminal-cyan/20 text-terminal-cyan font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all disabled:opacity-50"
          >
            {saving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? "PERSISTING PARAMS..." : "SAVE PARAMETERS"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default BotSettings;
