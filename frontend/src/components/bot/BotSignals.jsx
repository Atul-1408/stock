import React, { useState, useEffect } from "react";
import { Target, TrendingUp, TrendingDown, RefreshCw, CheckCircle2, Clock } from "lucide-react";
import api from "../../utils/api";

function BotSignals() {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 45000);
    return () => clearInterval(interval);
  }, []);

  const fetchSignals = async () => {
    try {
      const res = await api.get("/bot/signals?limit=50");
      setSignals(res.data.signals || []);
    } catch (err) {
      console.error("Error fetching signals feed:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredSignals =
    filter === "all"
      ? signals
      : signals.filter((s) => s.signal_type?.toUpperCase() === filter.toUpperCase());

  const buyCount = signals.filter((s) => s.signal_type === "BUY").length;
  const sellCount = signals.filter((s) => s.signal_type === "SELL").length;

  if (loading) {
    return (
      <div className="terminal-card py-12 flex flex-col items-center justify-center gap-3">
        <RefreshCw className="w-5 h-5 text-terminal-cyan animate-spin" />
        <span className="font-mono text-xs text-slate-400">Loading signal logs...</span>
      </div>
    );
  }

  return (
    <div className="terminal-card space-y-5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-terminal-800 pb-4">
        <div>
          <h2 className="font-mono text-sm uppercase font-bold text-slate-100 tracking-wider flex items-center gap-2">
            <Target className="w-4 h-4 text-terminal-cyan" />
            Autonomous Signal Ledger
          </h2>
          <p className="font-mono text-2xs text-slate-400 mt-0.5">
            Model inference outputs with composite sentiment, technical oscillators, and ML weights.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-1.5 p-1 rounded bg-terminal-950 border border-terminal-800">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1 rounded font-mono text-2xs uppercase tracking-wider transition-all ${
              filter === "all"
                ? "bg-terminal-800 text-slate-100 font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            All ({signals.length})
          </button>
          <button
            onClick={() => setFilter("buy")}
            className={`px-3 py-1 rounded font-mono text-2xs uppercase tracking-wider transition-all ${
              filter === "buy"
                ? "bg-terminal-emerald/20 text-terminal-emerald font-bold border border-terminal-emerald/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Buy ({buyCount})
          </button>
          <button
            onClick={() => setFilter("sell")}
            className={`px-3 py-1 rounded font-mono text-2xs uppercase tracking-wider transition-all ${
              filter === "sell"
                ? "bg-terminal-coral/20 text-terminal-coral font-bold border border-terminal-coral/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Sell ({sellCount})
          </button>
        </div>
      </div>

      {/* Signal Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredSignals.length > 0 ? (
          filteredSignals.map((signal) => {
            const isBuy = signal.signal_type === "BUY";
            const confidencePct = Math.round((signal.confidence || 0) * 100);

            return (
              <div
                key={signal.id || `${signal.ticker}-${signal.created_at}`}
                className="p-4 rounded border border-terminal-800 bg-terminal-950/60 hover:border-terminal-700 transition-colors flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-slate-100">{signal.ticker}</span>
                      <span
                        className={`px-2 py-0.5 rounded font-mono text-2xs font-semibold ${
                          isBuy ? "badge-positive" : "badge-negative"
                        }`}
                      >
                        {signal.signal_type}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="font-mono text-2xs text-slate-400">Confidence:</span>
                      <span className="font-mono text-xs font-bold text-slate-200 font-num">
                        {confidencePct}%
                      </span>
                    </div>
                  </div>

                  {/* Confidence progress */}
                  <div className="w-full bg-terminal-900 h-1 rounded overflow-hidden mb-3">
                    <div
                      className={`h-full ${isBuy ? "bg-terminal-emerald" : "bg-terminal-coral"}`}
                      style={{ width: `${confidencePct}%` }}
                    />
                  </div>

                  {/* Metrics Row */}
                  <div className="grid grid-cols-4 gap-2 font-mono text-2xs py-2 px-2.5 rounded bg-terminal-900/50 border border-terminal-850 mb-3">
                    <div>
                      <div className="text-slate-400">Target Prc</div>
                      <div className="font-bold text-slate-200 font-num">
                        {signal.price ? `$${Number(signal.price).toFixed(2)}` : "MKT"}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-400">Sentiment</div>
                      <div className="font-bold text-terminal-cyan font-num">
                        {signal.sentiment_score != null ? Number(signal.sentiment_score).toFixed(2) : "N/A"}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-400">Technical</div>
                      <div className="font-bold text-slate-200 font-num">
                        {signal.technical_score != null ? Number(signal.technical_score).toFixed(2) : "N/A"}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-400">ML Alpha</div>
                      <div className="font-bold text-slate-200 font-num">
                        {signal.ml_score != null ? Number(signal.ml_score).toFixed(2) : "N/A"}
                      </div>
                    </div>
                  </div>

                  {signal.reasoning && (
                    <p className="font-mono text-2xs text-slate-300 leading-relaxed mb-3">
                      {signal.reasoning}
                    </p>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-terminal-850 font-mono text-2xs text-slate-400">
                  <span
                    className={`inline-flex items-center gap-1.5 ${
                      signal.was_executed ? "text-terminal-emerald" : "text-slate-400"
                    }`}
                  >
                    {signal.was_executed ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>EXECUTED</span>
                      </>
                    ) : (
                      <>
                        <Clock className="w-3.5 h-3.5" />
                        <span>OBSERVED ONLY</span>
                      </>
                    )}
                  </span>
                  <span>{new Date(signal.created_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</span>
                </div>
              </div>
            );
          })
        ) : (
          <div className="col-span-2 py-12 text-center font-mono text-xs text-slate-400">
            No signals match active filter criteria.
          </div>
        )}
      </div>
    </div>
  );
}

export default BotSignals;
