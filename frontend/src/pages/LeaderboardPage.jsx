import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Trophy, TrendingUp, Users, Target, Activity, Share2, RefreshCw, Award } from "lucide-react";
import api from "../utils/api";
import { toast } from "react-toastify";

const LeaderboardPage = () => {
  const [leaderboard, setLeaderboard] = useState([]);
  const [myRank, setMyRank] = useState(null);
  const [period, setPeriod] = useState("all_time");
  const [loading, setLoading] = useState(true);

  const handleShare = (trader) => {
    const text = `Sovereign Intelligence Trader Rank #${trader.rank}: ${trader.username} (${trader.total_return_pct >= 0 ? "+" : ""}${trader.total_return_pct.toFixed(2)}% ROI, ${trader.win_rate.toFixed(1)}% Win Rate)`;
    if (navigator.share) {
      navigator.share({
        title: "Sovereign Intelligence Network",
        text: text,
        url: window.location.href
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text);
      toast.info("Trader telemetry copied to clipboard");
    }
  };

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      const [boardRes, rankRes] = await Promise.all([
        api.get(`/leaderboard?period=${period}`),
        api.get("/leaderboard/my-rank")
      ]);
      setLeaderboard(boardRes.data.leaderboard || []);
      setMyRank(rankRes.data.rank);
    } catch (error) {
      console.error("Error fetching leaderboard:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, [period]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-amber-400" />
            <h1 className="font-mono text-base font-bold text-slate-100 uppercase tracking-wider">
              Network Operator Rankings
            </h1>
          </div>
          <p className="font-mono text-xs text-slate-400 mt-0.5">
            Verified risk-adjusted performance ledger across sovereign intelligence accounts.
          </p>
        </div>

        {/* Timeframe Selectors */}
        <div className="flex items-center gap-1 p-1 rounded bg-terminal-950 border border-terminal-800">
          {[
            { id: "weekly", label: "7D Rolling" },
            { id: "monthly", label: "30D Rolling" },
            { id: "all_time", label: "Inception" }
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setPeriod(item.id)}
              className={`px-3 py-1.5 rounded font-mono text-xs uppercase tracking-wider transition-all ${
                period === item.id
                  ? "bg-terminal-cyan/15 text-terminal-cyan font-bold border border-terminal-cyan/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Operator Rank Tile */}
      {myRank && (
        <div className="terminal-card flex items-center justify-between bg-terminal-950/70 border-terminal-cyan/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded border border-terminal-cyan/30 bg-terminal-cyan/10 flex items-center justify-center text-terminal-cyan">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <div className="font-mono text-2xs uppercase tracking-wider text-terminal-cyan font-bold">
                Operator Global Standing
              </div>
              <div className="font-mono text-base font-bold text-slate-100 font-num">
                Rank #{myRank} Global Node
              </div>
            </div>
          </div>

          <div className="font-mono text-2xs text-slate-400">
            Based on active paper trading fills and portfolio equity growth.
          </div>
        </div>
      )}

      {/* Leaderboard Table */}
      <div className="terminal-card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-terminal-800 bg-terminal-950 text-slate-400 uppercase tracking-wider text-2xs">
                <th className="py-3 px-4">Rank</th>
                <th className="py-3 px-4">Operator Node</th>
                <th className="py-3 px-4 text-right">Return (ROI)</th>
                <th className="py-3 px-4 text-right">Hit Rate</th>
                <th className="py-3 px-4 text-right">Sharpe Ratio</th>
                <th className="py-3 px-4 text-right">Trades</th>
                <th className="py-3 px-4 text-center">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-850">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-16 text-center text-slate-400 font-mono text-xs">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="w-4 h-4 text-terminal-cyan animate-spin" />
                      <span>Synchronizing network ledger...</span>
                    </div>
                  </td>
                </tr>
              ) : leaderboard.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-16 text-center text-slate-400 font-mono text-xs">
                    No operator performance recorded for the selected window.
                  </td>
                </tr>
              ) : (
                leaderboard.map((trader) => {
                  const isTop1 = trader.rank === 1;
                  const isTop2 = trader.rank === 2;
                  const isTop3 = trader.rank === 3;
                  const returnPct = Number(trader.total_return_pct || 0);

                  return (
                    <tr
                      key={trader.user_id || trader.rank}
                      className="hover:bg-terminal-800/40 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center justify-center w-7 h-7 rounded font-bold text-xs font-num ${
                            isTop1
                              ? "bg-amber-400/15 border border-amber-400/40 text-amber-400"
                              : isTop2
                              ? "bg-slate-300/15 border border-slate-300/40 text-slate-300"
                              : isTop3
                              ? "bg-amber-700/15 border border-amber-700/40 text-amber-600"
                              : "text-slate-400"
                          }`}
                        >
                          #{trader.rank}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded border border-terminal-700 bg-terminal-950 flex items-center justify-center text-2xs uppercase font-bold text-slate-300">
                            {trader.username ? trader.username.slice(0, 2) : "OP"}
                          </div>
                          <div>
                            <span className="font-bold text-slate-100 uppercase">{trader.username}</span>
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-4 text-right">
                        <span
                          className={`font-bold font-num ${
                            returnPct >= 0 ? "text-terminal-emerald" : "text-terminal-coral"
                          }`}
                        >
                          {returnPct >= 0 ? "+" : ""}{returnPct.toFixed(2)}%
                        </span>
                      </td>

                      <td className="py-3 px-4 text-right text-slate-300 font-num">
                        {Number(trader.win_rate || 0).toFixed(1)}%
                      </td>

                      <td className="py-3 px-4 text-right text-terminal-cyan font-num">
                        {Number(trader.sharpe_ratio || 0).toFixed(2)}
                      </td>

                      <td className="py-3 px-4 text-right text-slate-400 font-num">
                        {trader.total_trades || 0}
                      </td>

                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => handleShare(trader)}
                          className="p-1.5 rounded hover:bg-terminal-800 text-slate-400 hover:text-terminal-cyan transition-colors"
                          title="Share operator stats"
                        >
                          <Share2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default LeaderboardPage;
