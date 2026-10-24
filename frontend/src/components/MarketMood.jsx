import React from "react";
import { BrainCircuit, TrendingUp, TrendingDown, Minus, AlertTriangle, HelpCircle } from "lucide-react";
import { moodFromAverage } from "../utils/sentiment";

export default function MarketMood({ sentiments }) {
  if (!sentiments || sentiments.length === 0) {
    return (
      <div className="terminal-card p-4 font-mono">
        <div className="flex items-center justify-between mb-2 border-b border-white/5 pb-2">
          <span className="text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
            <BrainCircuit size={14} className="text-cyan-400" />
            AI SENTIMENT BAROMETER
          </span>
          <span className="badge-neutral text-[9px] font-bold px-1.5 py-0.5 rounded">NO DATA</span>
        </div>
        <div className="py-4 text-center">
          <HelpCircle size={20} className="mx-auto text-slate-500 mb-1 opacity-60" />
          <p className="text-[11px] text-slate-400 font-semibold">NO HEADLINE DISPATCHES RECORDED</p>
          <p className="text-[10px] text-slate-500 mt-0.5">Sentiment metrics await new article ingestions</p>
        </div>
      </div>
    );
  }

  let posCount = 0;
  let negCount = 0;
  let neuCount = 0;
  let totalConfidence = 0;

  const totalScore = sentiments.reduce((sum, s) => {
    const safeScore = Number(s.sentiment_score ?? 0);
    totalConfidence += Number(s.confidence ?? 0.5);
    if (s.sentiment_label === "Positive") {
      posCount++;
      return sum + safeScore;
    }
    if (s.sentiment_label === "Negative") {
      negCount++;
      return sum - (safeScore < 0 ? Math.abs(safeScore) : safeScore);
    }
    neuCount++;
    return sum;
  }, 0);

  const average = totalScore / sentiments.length;
  const mood = moodFromAverage(average);
  const avgConfidencePct = Math.round((totalConfidence / sentiments.length) * 100);

  const posPct = Math.round((posCount / sentiments.length) * 100);
  const negPct = Math.round((negCount / sentiments.length) * 100);
  const neuPct = 100 - posPct - negPct;

  const isBull = mood.text === "BULLISH";
  const isBear = mood.text === "BEARISH";
  const isSufficient = sentiments.length >= 3;

  return (
    <div className="terminal-card p-4 flex flex-col justify-between font-mono">
      <div className="flex items-center justify-between mb-2.5 border-b border-white/5 pb-2">
        <span className="text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
          <BrainCircuit size={14} className="text-cyan-400" />
          AI SENTIMENT BAROMETER
        </span>
        <div className="flex items-center gap-1.5">
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              isBull ? "badge-positive" : isBear ? "badge-negative" : "badge-neutral"
            }`}
          >
            {mood.text} ({average >= 0 ? "+" : ""}{average.toFixed(2)})
          </span>
        </div>
      </div>

      {/* Low Sample Size Warning if fewer than 3 headlines */}
      {!isSufficient && (
        <div className="mb-2.5 px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-[10px] text-amber-400 flex items-center gap-1.5">
          <AlertTriangle size={12} className="shrink-0" />
          <span>LIMITED DATA (N={sentiments.length}) · Low statistical confidence</span>
        </div>
      )}

      {/* Distribution Progress Bar */}
      <div className="space-y-1.5 mb-3">
        <div className="h-2 rounded-full overflow-hidden flex bg-white/5">
          <div style={{ width: `${posPct}%` }} className="bg-emerald-500 transition-all duration-300" title={`Bullish: ${posPct}% (${posCount} articles)`} />
          <div style={{ width: `${neuPct}%` }} className="bg-slate-500 transition-all duration-300" title={`Neutral: ${neuPct}% (${neuCount} articles)`} />
          <div style={{ width: `${negPct}%` }} className="bg-coral-500 transition-all duration-300" title={`Bearish: ${negPct}% (${negCount} articles)`} />
        </div>

        <div className="flex justify-between text-[10px] text-slate-400 font-semibold">
          <span className="text-emerald-400 flex items-center gap-0.5" title={`${posCount} Bullish Articles`}>
            <TrendingUp size={10} /> {posPct}% BULL ({posCount})
          </span>
          <span className="text-slate-400 flex items-center gap-0.5" title={`${neuCount} Neutral Articles`}>
            <Minus size={10} /> {neuPct}% NEUT ({neuCount})
          </span>
          <span className="text-coral-400 flex items-center gap-0.5" title={`${negCount} Bearish Articles`}>
            <TrendingDown size={10} /> {negPct}% BEAR ({negCount})
          </span>
        </div>
      </div>

      {/* Numerical Metrics Strip */}
      <div className="grid grid-cols-2 gap-2 py-2 my-1 border-y border-white/5 text-[10px]">
        <div>
          <span className="text-slate-500 block uppercase">SAMPLE SIZE</span>
          <span className="text-white font-bold">{sentiments.length} HEADLINES</span>
        </div>
        <div className="text-right">
          <span className="text-slate-500 block uppercase">MODEL CONFIDENCE</span>
          <span className="text-cyan-400 font-bold">{avgConfidencePct}% AVG</span>
        </div>
      </div>

      <div className="text-[9px] text-slate-500 flex justify-between pt-1.5">
        <span>MODEL: FINBERT + VADER</span>
        <span>STATUS: {isSufficient ? "ROBUST SAMPLE" : "LOW DEPTH"}</span>
      </div>
    </div>
  );
}
