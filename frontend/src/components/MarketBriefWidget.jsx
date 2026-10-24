import React, { useState, useEffect } from "react";
import { Sparkles, CheckCircle2, AlertCircle, RefreshCw, Radio, Layers, Info } from "lucide-react";
import api from "../utils/api";

export default function MarketBriefWidget() {
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);

  const fetchBrief = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/market/brief");
      setBrief(res.data);
    } catch (err) {
      setError("Market brief generation temporarily unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBrief();
  }, []);

  if (loading) {
    return (
      <div className="terminal-card p-4 font-mono text-xs flex items-center justify-center gap-2 text-slate-400 min-h-[90px]">
        <RefreshCw size={13} className="animate-spin text-cyan-400" />
        <span>COMPUTING AI MARKET SYNTHESIS & INGESTING VERIFIED FACTS...</span>
      </div>
    );
  }

  if (error || !brief) {
    return null; // Gracefully collapses if unavailable
  }

  const verifiedFacts = brief.verified_facts || [];
  const influential = brief.influential_news || [];

  return (
    <div className="terminal-card p-4 font-mono text-xs space-y-3 border-cyan-500/20 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Sparkles size={13} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white tracking-wider text-[11px]">AI MARKET BRIEF</span>
              <span className="text-[9px] bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 font-bold px-1.5 py-0.5 rounded uppercase">
                {brief.overall_tone || "SYNTHESIS"}
              </span>
            </div>
            <div className="text-[10px] text-slate-500 flex items-center gap-1.5 mt-0.5">
              <span>WINDOW: {brief.time_window || "PAST 24H"}</span>
              <span>·</span>
              <span>SOURCES: {brief.data_sources?.length || 4} AUDITED FEEDS</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[10px] text-slate-400 hover:text-white px-2 py-1 rounded bg-white/5 hover:bg-white/10 transition-colors"
          >
            {expanded ? "COLLAPSE AUDIT" : "VIEW VERIFIED FACTS & CITATIONS"}
          </button>
          <button
            onClick={fetchBrief}
            title="Refresh Intelligence Brief"
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <RefreshCw size={12} />
          </button>
        </div>
      </div>

      {/* Narrative Synthesis (AI Interpretation) */}
      <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-slate-300 leading-relaxed text-[11px]">
        <div className="text-[9px] font-bold uppercase tracking-wider text-cyan-400 mb-1 flex items-center gap-1">
          <Radio size={10} className="animate-pulse" />
          AI INTERPRETATION (CAUSALITY NOT GUARANTEED)
        </div>
        <p>{brief.interpretation}</p>
      </div>

      {/* Expanded Audit Drawer: Verified Facts & Influential Dispatches */}
      {expanded && (
        <div className="space-y-3 pt-1 border-t border-white/5 text-[10px]">
          {/* Verified Facts List */}
          <div>
            <div className="text-slate-400 font-bold uppercase tracking-wider mb-1.5 flex items-center gap-1">
              <CheckCircle2 size={11} className="text-emerald-400" />
              VERIFIED INPUT FACTS
            </div>
            <ul className="space-y-1 pl-1">
              {verifiedFacts.map((fact, i) => (
                <li key={i} className="text-slate-300 flex items-start gap-1.5">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>{fact}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Influential News */}
          {influential.length > 0 && (
            <div>
              <div className="text-slate-400 font-bold uppercase tracking-wider mb-1.5 flex items-center gap-1">
                <Layers size={11} className="text-cyan-400" />
                KEY INFLUENCING DISPATCHES ({influential.length})
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {influential.map((item, idx) => {
                  const isPos = item.sentiment_label === "Positive";
                  const isNeg = item.sentiment_label === "Negative";
                  const badgeClass = isPos ? "badge-positive" : isNeg ? "badge-negative" : "badge-neutral";
                  return (
                    <div key={idx} className="p-2 rounded bg-black/40 border border-white/5 flex flex-col justify-between">
                      <div className="flex items-center justify-between text-[9px] mb-1">
                        <span className={`px-1 py-0.5 rounded font-bold ${badgeClass}`}>
                          {item.ticker}: {item.sentiment_label} ({item.sentiment_score > 0 ? "+" : ""}{item.sentiment_score.toFixed(2)})
                        </span>
                        <span className="text-slate-500 truncate max-w-[100px]">{item.source}</span>
                      </div>
                      <p className="text-slate-300 line-clamp-2 font-sans font-medium text-[11px] leading-snug">
                        {item.title}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Important Limitations & Disclaimer */}
          <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300/90 text-[10px] flex items-start gap-2">
            <Info size={13} className="shrink-0 mt-0.5" />
            <p className="leading-relaxed">{brief.disclaimer}</p>
          </div>
        </div>
      )}
    </div>
  );
}
