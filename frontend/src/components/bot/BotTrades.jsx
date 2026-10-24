import React, { useState, useEffect } from "react";
import { FileText, RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import api from "../../utils/api";

function BotTrades() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 45000);
    return () => clearInterval(interval);
  }, []);

  const fetchTrades = async () => {
    try {
      const res = await api.get("/bot/trades");
      setTrades(res.data.trades || []);
    } catch (err) {
      console.error("Error fetching trades ledger:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredTrades =
    filter === "all"
      ? trades
      : trades.filter((t) => t.status?.toUpperCase() === filter.toUpperCase());

  const openCount = trades.filter((t) => t.status === "OPEN").length;
  const closedCount = trades.filter((t) => t.status === "CLOSED").length;

  const calculateStats = () => {
    const closed = trades.filter((t) => t.status === "CLOSED");
    if (closed.length === 0) return { wins: 0, losses: 0, totalPnL: 0, avgWin: 0, avgLoss: 0 };

    const wins = closed.filter((t) => t.pnl > 0).length;
    const losses = closed.filter((t) => t.pnl < 0).length;
    const totalPnL = closed.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const wins_pnl = closed.filter((t) => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0);
    const losses_pnl = closed.filter((t) => t.pnl < 0).reduce((sum, t) => sum + t.pnl, 0);

    return {
      wins,
      losses,
      totalPnL,
      avgWin: wins > 0 ? wins_pnl / wins : 0,
      avgLoss: losses > 0 ? losses_pnl / losses : 0
    };
  };

  const stats = calculateStats();

  if (loading) {
    return (
      <div className="terminal-card py-12 flex flex-col items-center justify-center gap-3">
        <RefreshCw className="w-5 h-5 text-terminal-cyan animate-spin" />
        <span className="font-mono text-xs text-slate-400">Loading trade execution ledger...</span>
      </div>
    );
  }

  return (
    <div className="terminal-card space-y-5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-terminal-800 pb-4">
        <div>
          <h2 className="font-mono text-sm uppercase font-bold text-slate-100 tracking-wider flex items-center gap-2">
            <FileText className="w-4 h-4 text-terminal-cyan" />
            Execution Ledger & Order Audit
          </h2>
          <p className="font-mono text-2xs text-slate-400 mt-0.5">
            Full audit log of autonomous order dispatch, exit fills, and realized performance.
          </p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-1.5 p-1 rounded bg-terminal-950 border border-terminal-800">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1 rounded font-mono text-2xs uppercase tracking-wider transition-all ${
              filter === "all"
                ? "bg-terminal-800 text-slate-100 font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            All ({trades.length})
          </button>
          <button
            onClick={() => setFilter("open")}
            className={`px-3 py-1 rounded font-mono text-2xs uppercase tracking-wider transition-all ${
              filter === "open"
                ? "bg-terminal-cyan/20 text-terminal-cyan font-bold border border-terminal-cyan/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Open ({openCount})
          </button>
          <button
            onClick={() => setFilter("closed")}
            className={`px-3 py-1 rounded font-mono text-2xs uppercase tracking-wider transition-all ${
              filter === "closed"
                ? "bg-terminal-emerald/20 text-terminal-emerald font-bold border border-terminal-emerald/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Closed ({closedCount})
          </button>
        </div>
      </div>

      {/* Ledger Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded border border-terminal-800 bg-terminal-950/60 font-mono">
          <div className="text-2xs uppercase text-slate-400">Realized P&L</div>
          <div
            className={`text-sm font-bold font-num mt-0.5 ${
              stats.totalPnL >= 0 ? "text-terminal-emerald" : "text-terminal-coral"
            }`}
          >
            {stats.totalPnL >= 0 ? "+" : ""}${stats.totalPnL.toFixed(2)}
          </div>
        </div>

        <div className="p-3 rounded border border-terminal-800 bg-terminal-950/60 font-mono">
          <div className="text-2xs uppercase text-slate-400">Wins / Losses</div>
          <div className="text-sm font-bold text-slate-200 font-num mt-0.5">
            <span className="text-terminal-emerald">{stats.wins}</span>
            <span className="text-slate-500"> / </span>
            <span className="text-terminal-coral">{stats.losses}</span>
          </div>
        </div>

        <div className="p-3 rounded border border-terminal-800 bg-terminal-950/60 font-mono">
          <div className="text-2xs uppercase text-slate-400">Avg Win</div>
          <div className="text-sm font-bold text-terminal-emerald font-num mt-0.5">
            +${stats.avgWin.toFixed(2)}
          </div>
        </div>

        <div className="p-3 rounded border border-terminal-800 bg-terminal-950/60 font-mono">
          <div className="text-2xs uppercase text-slate-400">Avg Loss</div>
          <div className="text-sm font-bold text-terminal-coral font-num mt-0.5">
            -${Math.abs(stats.avgLoss).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-terminal-800 rounded">
        {filteredTrades.length > 0 ? (
          <table className="w-full text-left border-collapse font-mono text-2xs">
            <thead>
              <tr className="border-b border-terminal-800 bg-terminal-950 text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Ticker</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3 text-right">Units</th>
                <th className="py-2.5 px-3 text-right">Entry</th>
                <th className="py-2.5 px-3 text-right">Exit</th>
                <th className="py-2.5 px-3 text-right">P&L ($)</th>
                <th className="py-2.5 px-3 text-right">P&L (%)</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-3">Entry Time</th>
                <th className="py-2.5 px-3">Exit Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-850">
              {filteredTrades.map((trade) => {
                const pnl = Number(trade.pnl || 0);
                const pnlPct = Number(trade.pnl_pct || 0);
                const isProfit = pnl >= 0;

                return (
                  <tr key={trade.id} className="hover:bg-terminal-800/40 transition-colors">
                    <td className="py-2.5 px-3 font-bold text-slate-100">{trade.ticker}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-1.5 py-0.2 rounded font-semibold ${
                          trade.action === "BUY" ? "badge-positive" : "badge-negative"
                        }`}
                      >
                        {trade.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-300 font-num">{trade.shares}</td>
                    <td className="py-2.5 px-3 text-right text-slate-200 font-num">
                      ${Number(trade.entry_price || 0).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-200 font-num">
                      {trade.exit_price ? `$${Number(trade.exit_price).toFixed(2)}` : "—"}
                    </td>
                    <td
                      className={`py-2.5 px-3 text-right font-bold font-num ${
                        isProfit ? "text-terminal-emerald" : "text-terminal-coral"
                      }`}
                    >
                      {trade.status === "CLOSED" ? `${isProfit ? "+" : ""}$${pnl.toFixed(2)}` : "—"}
                    </td>
                    <td
                      className={`py-2.5 px-3 text-right font-bold font-num ${
                        isProfit ? "text-terminal-emerald" : "text-terminal-coral"
                      }`}
                    >
                      {trade.status === "CLOSED" ? `${isProfit ? "+" : ""}${pnlPct.toFixed(2)}%` : "—"}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`inline-block px-1.5 py-0.2 rounded font-semibold ${
                          trade.status === "OPEN"
                            ? "bg-terminal-cyan/15 text-terminal-cyan border border-terminal-cyan/30"
                            : "bg-terminal-800 text-slate-300"
                        }`}
                      >
                        {trade.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {trade.entry_time
                        ? new Date(trade.entry_time).toLocaleString([], { dateStyle: "short", timeStyle: "short" })
                        : "—"}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {trade.exit_time
                        ? new Date(trade.exit_time).toLocaleString([], { dateStyle: "short", timeStyle: "short" })
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <div className="py-12 text-center font-mono text-xs text-slate-400">
            No trade execution history found.
          </div>
        )}
      </div>
    </div>
  );
}

export default BotTrades;
