import React from "react";
import { motion } from "framer-motion";
import { History, ArrowUpRight, ArrowDownLeft, Clock, Activity } from "lucide-react";

const TransactionHistory = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="terminal-card py-6 text-center font-mono text-xs text-slate-400">
        Loading ledger activity...
      </div>
    );
  }

  if (!data || data.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 font-mono text-xs uppercase font-bold text-slate-300 tracking-wider">
        <History className="w-4 h-4 text-terminal-cyan" />
        <span>Recent Execution Activity</span>
      </div>

      <div className="space-y-2">
        {data.map((tx) => {
          const isBuy = tx.action === "BUY";
          return (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              key={tx.id}
              className="p-3 rounded border border-terminal-800 bg-terminal-950/60 flex items-center justify-between font-mono text-xs hover:border-terminal-700 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-7 h-7 rounded flex items-center justify-center ${
                    isBuy
                      ? "bg-terminal-emerald/15 text-terminal-emerald"
                      : "bg-terminal-coral/15 text-terminal-coral"
                  }`}
                >
                  {isBuy ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownLeft className="w-4 h-4" />}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-100">{tx.ticker}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded font-semibold text-2xs ${
                        isBuy ? "badge-positive" : "badge-negative"
                      }`}
                    >
                      {tx.action}
                    </span>
                    <span className="text-slate-400 text-2xs font-num">
                      {tx.shares} unit{tx.shares === 1 ? "" : "s"} @ ${tx.price?.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-2xs text-slate-400 mt-0.5">
                    {new Date(tx.timestamp).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="font-bold text-slate-200 font-num">
                  ${((tx.shares || 0) * (tx.price || 0)).toFixed(2)}
                </div>
                {tx.sentiment_label && (
                  <div className="text-2xs text-terminal-cyan">
                    Sentiment: {tx.sentiment_label}
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default TransactionHistory;
