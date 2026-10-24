import React from "react";
import { motion } from "framer-motion";
import { Briefcase, TrendingUp, TrendingDown, Layers } from "lucide-react";

const Portfolio = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="terminal-card py-12 text-center font-mono text-xs text-slate-400">
        Loading portfolio ledger...
      </div>
    );
  }

  if (!data || !data.holdings || data.holdings.length === 0) {
    return (
      <div className="terminal-card py-12 text-center font-mono text-xs text-slate-400">
        <Briefcase className="w-8 h-8 text-terminal-800 mx-auto mb-2" />
        <div className="font-bold uppercase text-slate-300">No Open Holdings</div>
        <p className="text-2xs text-slate-400 mt-1 font-sans">
          Execute a trade order in the Trade Desk to initiate inventory.
        </p>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="terminal-card">
          <p className="font-mono text-2xs uppercase tracking-wider text-slate-400">Total Market Value</p>
          <div className="flex items-center justify-between mt-1">
            <p className="font-mono text-2xl font-bold text-slate-100 font-num">
              ${(data.total_market_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <Layers className="w-5 h-5 text-terminal-cyan" />
          </div>
        </div>

        <div className="terminal-card">
          <p className="font-mono text-2xs uppercase tracking-wider text-slate-400">Unrealized P&L</p>
          <div className="flex items-center justify-between mt-1">
            <p
              className={`font-mono text-2xl font-bold font-num ${
                (data.total_pnl || 0) >= 0 ? "text-terminal-emerald" : "text-terminal-coral"
              }`}
            >
              {(data.total_pnl || 0) >= 0 ? "+" : ""}$
              {(data.total_pnl || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            {(data.total_pnl || 0) >= 0 ? (
              <TrendingUp className="w-5 h-5 text-terminal-emerald" />
            ) : (
              <TrendingDown className="w-5 h-5 text-terminal-coral" />
            )}
          </div>
        </div>
      </div>

      <div className="terminal-card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-terminal-800 bg-terminal-950 text-slate-400 uppercase tracking-wider text-2xs">
                <th className="py-2.5 px-4">Asset</th>
                <th className="py-2.5 px-4 text-right">Shares</th>
                <th className="py-2.5 px-4 text-right">Avg Price</th>
                <th className="py-2.5 px-4 text-right">Current</th>
                <th className="py-2.5 px-4 text-right">Market Value</th>
                <th className="py-2.5 px-4 text-right">P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-850">
              {data.holdings.map((holding) => {
                const isProfitable = (holding.pnl || 0) >= 0;
                return (
                  <tr key={holding.ticker} className="hover:bg-terminal-800/40 transition-colors">
                    <td className="py-2.5 px-4 font-bold text-slate-100">{holding.ticker}</td>
                    <td className="py-2.5 px-4 text-right text-slate-300 font-num">{holding.shares}</td>
                    <td className="py-2.5 px-4 text-right text-slate-300 font-num">${holding.avg_price?.toFixed(2)}</td>
                    <td className="py-2.5 px-4 text-right text-slate-200 font-num">${holding.current_price?.toFixed(2)}</td>
                    <td className="py-2.5 px-4 text-right text-slate-200 font-num">
                      ${(holding.market_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td
                      className={`py-2.5 px-4 text-right font-bold font-num ${
                        isProfitable ? "text-terminal-emerald" : "text-terminal-coral"
                      }`}
                    >
                      {isProfitable ? "+" : ""}${holding.pnl?.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
};

export default Portfolio;
