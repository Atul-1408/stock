import React from "react";
import { ExternalLink, Radio } from "lucide-react";

export default function NewsFeed({ news }) {
  if (!news || news.length === 0) {
    return (
      <div className="terminal-card p-6 text-center border-dashed">
        <Radio className="w-6 h-6 text-slate-500 mx-auto mb-2 opacity-50" />
        <p className="font-mono text-xs text-slate-400 font-semibold">NO NEWS DISPATCHES FOR THIS SYMBOL</p>
        <p className="text-[11px] text-slate-500 mt-1">Live news wire awaiting new headline ingestions</p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between px-1">
        <span className="font-mono text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
          <Radio size={13} className="text-cyan-400 animate-pulse" />
          INTELLIGENCE WIRE ({news.length})
        </span>
        <span className="text-[10px] font-mono text-slate-500">REAL-TIME SENTIMENT</span>
      </div>

      <div className="space-y-2 max-h-[480px] overflow-y-auto custom-scrollbar pr-1">
        {news.map((article, idx) => {
          const isPos = article.sentiment_label === "Positive";
          const isNeg = article.sentiment_label === "Negative";
          const label = isPos ? "BULLISH" : isNeg ? "BEARISH" : "NEUTRAL";
          const badgeClass = isPos ? "badge-positive" : isNeg ? "badge-negative" : "badge-neutral";
          const conf = article.confidence ? Math.round(article.confidence * 100) : null;
          const status = article.processing_status ? article.processing_status.toUpperCase() : "LIVE";
          const pubDate = article.published_at ? article.published_at.slice(0, 16).replace("T", " ") : null;

          return (
            <div
              key={article.url || idx}
              className="terminal-card terminal-card-interactive p-3 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between gap-2 mb-1.5 font-mono text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className={`px-1.5 py-0.5 rounded font-bold ${badgeClass}`}>
                    {label} {article.sentiment_score ? `(${article.sentiment_score > 0 ? "+" : ""}${Number(article.sentiment_score).toFixed(2)})` : ""}
                  </span>
                  {conf != null && (
                    <span className="text-slate-400 font-medium">
                      {conf}% CONF
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5 text-slate-400 font-semibold">
                  <span className="text-[9px] text-slate-500 bg-white/5 px-1 py-0.5 rounded">
                    {status}
                  </span>
                  <span className="truncate max-w-[120px]">
                    {article.source || "WIRE FEED"}
                  </span>
                </div>
              </div>

              <h3 className="text-xs font-semibold leading-relaxed text-slate-200 line-clamp-2">
                {article.title}
              </h3>

              <div className="mt-2 pt-1.5 border-t border-white/5 flex items-center justify-between font-mono text-[9px] text-slate-500">
                <span>{pubDate || "RECENT"}</span>
                {article.url && (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-bold text-cyan-400 hover:text-cyan-300 transition-colors"
                  >
                    <span>SOURCE</span>
                    <ExternalLink size={9} />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
