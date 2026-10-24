import React, { useState, useEffect } from "react";
import { Activity, AlertTriangle, TrendingUp, TrendingDown, Minus, Info, ShieldAlert } from "lucide-react";
import api from "../utils/api";

export default function StockIntelligenceCard({ symbol }) {
  const [intel, setIntel] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol) return;
    let mounted = true;
    setLoading(true);

    api
      .get(`/stocks/${symbol}/intelligence`)
      .then((res) => {
        if (mounted) setIntel(res.data);
      })
      .catch(() => {
        if (mounted) setIntel(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [symbol]);

  if (loading || !intel) return null;

  const priceMetrics = intel.price_metrics || {};
  const sentimentMetrics = intel.sentiment_metrics || {};
  const isUp = (priceMetrics.change_7d_pct || 0) >= 0;
  const isSufficient = sentimentMetrics.is_sufficient_data;

  return (
    <div className="terminal-card p-4 font-mono text-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <span className="font-bold text-white tracking-wider flex items-center gap-1.5 text-xs">
          <Activity size={14} className="text-cyan-400" />
          {symbol} SYNTHESIS & PRICE DYNAMICS
        </span>
        <span
          className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
            isSufficient ? "badge-positive" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
          }`}
        >
          {isSufficient ? "ROBUST DATA" : "LIMITED DATA"}
        </span>
      </div>

      {/* Key Metric Gauges */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
        <div className="p-2 rounded bg-white/5">
          <span className="text-slate-400 block uppercase">7D RETURN</span>
          <span className={`text-xs font-bold flex items-center gap-0.5 mt-0.5 ${isUp ? "text-emerald-400" : "text-coral-400"}`}>
            {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
            {isUp ? "+" : ""}{priceMetrics.change_7d_pct?.toFixed(2)}%
          </span>
        </div>

        <div className="p-2 rounded bg-white/5">
          <span className="text-slate-400 block uppercase">30D BOUNDS</span>
          <span className="text-xs font-bold text-white mt-0.5 block truncate">
            ${priceMetrics.low_30d?.toFixed(1)} - ${priceMetrics.high_30d?.toFixed(1)}
          </span>
        </div>

        <div className="p-2 rounded bg-white/5">
          <span className="text-slate-400 block uppercase">SENTIMENT SCORE</span>
          <span className="text-xs font-bold text-cyan-400 mt-0.5 block">
            {sentimentMetrics.score > 0 ? "+" : ""}{sentimentMetrics.score?.toFixed(2)} ({sentimentMetrics.label})
          </span>
        </div>

        <div className="p-2 rounded bg-white/5">
          <span className="text-slate-400 block uppercase">HEADLINES AUDITED</span>
          <span className="text-xs font-bold text-slate-200 mt-0.5 block">
            {sentimentMetrics.sample_size || 0} ARTICLES
          </span>
        </div>
      </div>

      {/* Narrative Synthesis */}
      <div className="p-2.5 rounded bg-black/40 border border-white/5 text-slate-300 leading-relaxed text-[11px] font-sans">
        {intel.summary}
      </div>

      {/* Limitation Disclosure */}
      <div className="p-2 rounded bg-white/5 border border-white/5 text-slate-400 text-[10px] flex items-start gap-1.5">
        <ShieldAlert size={12} className="shrink-0 text-amber-400 mt-0.5" />
        <span className="leading-snug">{intel.limitations}</span>
      </div>
    </div>
  );
}
