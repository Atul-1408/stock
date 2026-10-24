import React, { useState, useEffect } from "react";
import { Eye, Plus, Trash2, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import api from "../../utils/api";

function BotWatchlist({ onUpdate }) {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newTicker, setNewTicker] = useState("");
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const res = await api.get("/bot/watchlist");
      setWatchlist(res.data.watchlist || []);
    } catch (err) {
      console.error("Error fetching bot watchlist:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTicker = async (e) => {
    e.preventDefault();
    const tickerClean = newTicker.trim().toUpperCase();
    if (!tickerClean) return;

    setAdding(true);
    setMessage("");
    setError("");

    try {
      await api.post("/bot/watchlist", { ticker: tickerClean });
      setMessage(`Added ${tickerClean} to target universe.`);
      setNewTicker("");
      await fetchWatchlist();
      onUpdate?.();
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setError(`Failed to add ${tickerClean}. Symbol may already be monitored.`);
      setTimeout(() => setError(""), 3500);
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveTicker = async (ticker) => {
    if (!window.confirm(`Are you sure you want to remove ${ticker} from the monitored universe?`)) {
      return;
    }
    setMessage("");
    setError("");
    try {
      await api.delete(`/bot/watchlist/${ticker}`);
      setMessage(`Removed ${ticker} from monitored symbols.`);
      await fetchWatchlist();
      onUpdate?.();
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setError(`Failed to remove ${ticker}.`);
      setTimeout(() => setError(""), 3000);
    }
  };

  if (loading) {
    return (
      <div className="terminal-card py-12 flex flex-col items-center justify-center gap-3">
        <RefreshCw className="w-5 h-5 text-terminal-cyan animate-spin" />
        <span className="font-mono text-xs text-slate-400">Loading monitored universe...</span>
      </div>
    );
  }

  return (
    <div className="terminal-card space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-terminal-800 pb-4">
        <div>
          <h2 className="font-mono text-sm uppercase font-bold text-slate-100 tracking-wider flex items-center gap-2">
            <Eye className="w-4 h-4 text-terminal-cyan" />
            Monitored Universe & Asset Watchlist
          </h2>
          <p className="font-mono text-2xs text-slate-400 mt-0.5">
            Symbols continuously polled for sentiment spikes, order book shifts, and technical breakouts.
          </p>
        </div>
      </div>

      {message && (
        <div className="p-3 rounded border border-terminal-emerald/30 bg-terminal-emerald/10 text-terminal-emerald font-mono text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded border border-terminal-coral/30 bg-terminal-coral/10 text-terminal-coral font-mono text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Add Symbol Input */}
      <form onSubmit={handleAddTicker} className="flex gap-2 max-w-md">
        <input
          type="text"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
          placeholder="ENTER TICKER (E.G. NVDA, TSLA)"
          maxLength="10"
          className="flex-1 bg-terminal-950 border border-terminal-700 rounded px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-terminal-cyan"
        />
        <button
          type="submit"
          disabled={adding || !newTicker.trim()}
          className="px-4 py-2 rounded bg-terminal-cyan/10 border border-terminal-cyan/40 hover:bg-terminal-cyan/20 text-terminal-cyan font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 disabled:opacity-40 transition-all"
        >
          {adding ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
          Add Asset
        </button>
      </form>

      {/* Grid of Monitored Tickers */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {watchlist.length > 0 ? (
          watchlist.map((item) => (
            <div
              key={item.id || item.ticker}
              className="p-3 rounded border border-terminal-800 bg-terminal-950/70 hover:border-terminal-700 transition-colors flex items-center justify-between group"
            >
              <div>
                <div className="font-mono text-sm font-bold text-slate-100">{item.ticker}</div>
                <div className="font-mono text-2xs text-slate-400">
                  {item.added_at ? new Date(item.added_at).toLocaleDateString([], { month: "short", day: "numeric" }) : "Active"}
                </div>
              </div>

              <button
                onClick={() => handleRemoveTicker(item.ticker)}
                title="Remove symbol"
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-terminal-coral/20 text-slate-500 hover:text-terminal-coral transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        ) : (
          <div className="col-span-full py-12 text-center font-mono text-xs text-slate-400">
            No symbols registered in the algorithmic universe. Add symbols above to engage polling.
          </div>
        )}
      </div>

      <div className="p-3 rounded border border-terminal-800 bg-terminal-950/40 font-mono text-2xs text-slate-400 flex items-center gap-2">
        <span className="text-terminal-cyan uppercase font-bold">INFO:</span>
        <span>The autonomous model executes polling cycles exclusively on assets registered in this universe.</span>
      </div>
    </div>
  );
}

export default BotWatchlist;
