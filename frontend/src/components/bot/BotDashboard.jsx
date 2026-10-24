import React, { useState, useEffect } from "react";
import { 
  Bot, 
  Play, 
  Square, 
  Activity, 
  Target, 
  TrendingUp, 
  TrendingDown, 
  Sliders, 
  Eye, 
  FileText, 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw 
} from "lucide-react";
import api from "../../utils/api";
import BotSettings from "./BotSettings";
import BotWatchlist from "./BotWatchlist";
import BotSignals from "./BotSignals";
import BotTrades from "./BotTrades";

function BotDashboard() {
  const [status, setStatus] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchBotData();
    const interval = setInterval(fetchBotData, 20000);
    return () => clearInterval(interval);
  }, []);

  const fetchBotData = async () => {
    try {
      setError(null);
      const [statusRes, perfRes] = await Promise.all([
        api.get("/bot/status"),
        api.get("/bot/performance")
      ]);
      setStatus(statusRes.data);
      setPerformance(perfRes.data);
    } catch (err) {
      console.error("Error fetching bot telemetry:", err);
      setError("Telemetry disconnect: unable to retrieve bot state.");
    } finally {
      setLoading(false);
    }
  };

  const toggleBot = async () => {
    if (status?.is_active && !window.confirm("Are you sure you want to halt the autonomous execution engine?")) {
      return;
    }
    setActionLoading(true);
    try {
      if (status?.is_active) {
        await api.post("/bot/stop", {});
      } else {
        await api.post("/bot/start", {});
      }
      await fetchBotData();
    } catch (err) {
      setError("Failed to execute bot state transition.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <RefreshCw className="w-6 h-6 text-terminal-cyan animate-spin" />
        <span className="font-mono text-xs uppercase tracking-widest text-slate-400">
          Syncing Autonomous Execution Telemetry...
        </span>
      </div>
    );
  }

  const isActive = Boolean(status?.is_active);
  const totalTrades = performance?.total_trades || 0;
  const winRate = Number(performance?.win_rate || 0);
  const totalPnl = Number(performance?.total_pnl || 0);
  const avgProfit = Number(performance?.avg_profit || 0);
  const avgLoss = Number(performance?.avg_loss || 0);

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "signals", label: "Signals", icon: Target },
    { id: "trades", label: "Trades", icon: FileText },
    { id: "watchlist", label: `Watchlist (${status?.watchlist?.length || 0})`, icon: Eye },
    { id: "settings", label: "Strategy Parameters", icon: Sliders }
  ];

  return (
    <div className="space-y-6">
      {/* Bot Control Strip */}
      <div className="terminal-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded border border-terminal-700 bg-terminal-950 flex items-center justify-center text-terminal-cyan shrink-0">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-base font-bold text-slate-100 tracking-wider uppercase">
                {status?.config?.bot_name || "SOVEREIGN ALGO DESK"}
              </h1>
              <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-2xs font-mono uppercase font-semibold border ${
                  isActive
                    ? "bg-terminal-emerald/10 border-terminal-emerald/30 text-terminal-emerald"
                    : "bg-terminal-coral/10 border-terminal-coral/30 text-terminal-coral"
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isActive ? "bg-terminal-emerald animate-pulse" : "bg-terminal-coral"}`} />
                {isActive ? "ENGINE ACTIVE" : "ENGINE SUSPENDED"}
              </span>
            </div>
            <p className="font-mono text-xs text-slate-400">
              Autonomous execution node &bull; Mode: {status?.config?.risk_level || "MEDIUM"} RISK &bull; 
              Polling interval: 30s
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchBotData}
            title="Refresh telemetry"
            className="p-2 rounded border border-terminal-700 hover:border-terminal-600 bg-terminal-900 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={toggleBot}
            disabled={actionLoading}
            className={`px-4 py-2 rounded font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 border transition-all ${
              isActive
                ? "bg-terminal-coral/10 border-terminal-coral/40 text-terminal-coral hover:bg-terminal-coral/20"
                : "bg-terminal-emerald/10 border-terminal-emerald/40 text-terminal-emerald hover:bg-terminal-emerald/20"
            }`}
          >
            {actionLoading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : isActive ? (
              <Square className="w-3.5 h-3.5 fill-current" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            {isActive ? "HALT ENGINE" : "ENGAGE ENGINE"}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded border border-terminal-coral/30 bg-terminal-coral/10 text-terminal-coral font-mono text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Institutional KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="terminal-card">
          <div className="font-mono text-2xs uppercase tracking-wider text-slate-400">Total Executions</div>
          <div className="font-mono text-xl font-bold text-slate-100 mt-1">{totalTrades}</div>
          <div className="font-mono text-2xs text-slate-400 mt-1 flex items-center gap-1.5">
            <span className="text-terminal-emerald">{performance?.winning_trades || 0}W</span>
            <span>/</span>
            <span className="text-terminal-coral">{performance?.losing_trades || 0}L</span>
          </div>
        </div>

        <div className="terminal-card">
          <div className="font-mono text-2xs uppercase tracking-wider text-slate-400">Hit Rate (Win %)</div>
          <div className="font-mono text-xl font-bold text-slate-100 mt-1 font-num">
            {winRate.toFixed(1)}%
          </div>
          <div className="mt-1">
            <span
              className={`inline-block px-1.5 py-0.2 rounded font-mono text-2xs font-semibold ${
                winRate >= 50 ? "badge-positive" : "badge-negative"
              }`}
            >
              Benchmark: 55.0%
            </span>
          </div>
        </div>

        <div className="terminal-card">
          <div className="font-mono text-2xs uppercase tracking-wider text-slate-400">Cumulative Realized P&L</div>
          <div
            className={`font-mono text-xl font-bold mt-1 font-num ${
              totalPnl >= 0 ? "text-terminal-emerald" : "text-terminal-coral"
            }`}
          >
            {totalPnl >= 0 ? "+" : ""}${totalPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="font-mono text-2xs text-slate-400 mt-1">Net of simulated slip</div>
        </div>

        <div className="terminal-card">
          <div className="font-mono text-2xs uppercase tracking-wider text-slate-400">Avg Win / Loss</div>
          <div className="font-mono text-sm font-bold text-slate-100 mt-1 font-num flex items-center justify-between">
            <span className="text-terminal-emerald">+${avgProfit.toFixed(2)}</span>
            <span className="text-slate-600">|</span>
            <span className="text-terminal-coral">-${Math.abs(avgLoss).toFixed(2)}</span>
          </div>
          <div className="font-mono text-2xs text-slate-400 mt-1">
            Profit Factor: {avgLoss !== 0 ? (Math.abs(avgProfit / avgLoss)).toFixed(2) : "N/A"}
          </div>
        </div>
      </div>

      {/* Desk Tab Switcher */}
      <div className="flex border-b border-terminal-800 gap-1 overflow-x-auto no-scrollbar">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 font-mono text-xs uppercase tracking-wider transition-all border-b-2 -mb-px whitespace-nowrap ${
                isSelected
                  ? "border-terminal-cyan text-terminal-cyan bg-terminal-cyan/5 font-bold"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:border-terminal-700"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Signals Stream */}
            <div className="terminal-card flex flex-col">
              <div className="flex items-center justify-between border-b border-terminal-800 pb-3 mb-4">
                <div className="font-mono text-xs uppercase font-bold text-slate-200 tracking-wider flex items-center gap-2">
                  <Target className="w-4 h-4 text-terminal-cyan" />
                  Latest Model Signals
                </div>
                <button
                  onClick={() => setActiveTab("signals")}
                  className="font-mono text-2xs text-terminal-cyan hover:underline uppercase"
                >
                  View Full Feed &rarr;
                </button>
              </div>

              <div className="space-y-3 flex-1 overflow-y-auto max-h-[460px] pr-1">
                {status?.recent_signals && status.recent_signals.length > 0 ? (
                  status.recent_signals.slice(0, 6).map((signal) => (
                    <div
                      key={signal.id || `${signal.ticker}-${signal.created_at}`}
                      className="p-3 rounded border border-terminal-800 bg-terminal-950/60 hover:border-terminal-700 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-100">{signal.ticker}</span>
                          <span
                            className={`px-1.5 py-0.2 rounded font-mono text-2xs font-semibold ${
                              signal.signal_type === "BUY" ? "badge-positive" : "badge-negative"
                            }`}
                          >
                            {signal.signal_type}
                          </span>
                        </div>
                        <div className="font-mono text-xs text-slate-300 font-num">
                          {signal.price ? `$${Number(signal.price).toFixed(2)}` : "MKT"}
                        </div>
                      </div>

                      <div className="flex items-center justify-between font-mono text-2xs text-slate-400 mb-1.5">
                        <span>Confidence: {((signal.confidence || 0) * 100).toFixed(0)}%</span>
                        <span>{new Date(signal.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>

                      <div className="w-full bg-terminal-900 h-1 rounded overflow-hidden mb-2">
                        <div
                          className={`h-full ${signal.signal_type === "BUY" ? "bg-terminal-emerald" : "bg-terminal-coral"}`}
                          style={{ width: `${Math.min(100, (signal.confidence || 0) * 100)}%` }}
                        />
                      </div>

                      {signal.reasoning && (
                        <p className="font-mono text-2xs text-slate-300 line-clamp-2">
                          {signal.reasoning}
                        </p>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="py-12 text-center font-mono text-xs text-slate-400">
                    No active algorithmic signals generated yet.
                  </div>
                )}
              </div>
            </div>

            {/* Open Positions Ledger */}
            <div className="terminal-card flex flex-col">
              <div className="flex items-center justify-between border-b border-terminal-800 pb-3 mb-4">
                <div className="font-mono text-xs uppercase font-bold text-slate-200 tracking-wider flex items-center gap-2">
                  <Activity className="w-4 h-4 text-terminal-emerald" />
                  Active Model Exposure
                </div>
                <span className="font-mono text-2xs text-slate-400">
                  {status?.open_positions?.length || 0} open
                </span>
              </div>

              <div className="space-y-3 flex-1 overflow-y-auto max-h-[460px] pr-1">
                {status?.open_positions && status.open_positions.length > 0 ? (
                  status.open_positions.map((pos) => (
                    <div
                      key={pos.id || `${pos.ticker}-${pos.entry_price}`}
                      className="p-3 rounded border border-terminal-800 bg-terminal-950/60"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-100">{pos.ticker}</span>
                          <span className="font-mono text-2xs text-slate-400">
                            {pos.shares} {pos.shares === 1 ? "unit" : "units"}
                          </span>
                        </div>
                        <span className="badge-cyan font-mono text-2xs">LONG</span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 font-mono text-2xs pt-2 border-t border-terminal-850">
                        <div>
                          <div className="text-slate-400">Entry</div>
                          <div className="font-bold text-slate-200 font-num">
                            ${pos.entry_price ? Number(pos.entry_price).toFixed(2) : "0.00"}
                          </div>
                        </div>
                        <div>
                          <div className="text-slate-400">Stop Loss</div>
                          <div className="font-bold text-terminal-coral font-num">
                            {pos.stop_loss ? `$${Number(pos.stop_loss).toFixed(2)}` : "N/A"}
                          </div>
                        </div>
                        <div>
                          <div className="text-slate-400">Take Profit</div>
                          <div className="font-bold text-terminal-emerald font-num">
                            {pos.take_profit ? `$${Number(pos.take_profit).toFixed(2)}` : "N/A"}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-12 text-center font-mono text-xs text-slate-400">
                    No active positions held by engine.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "settings" && <BotSettings onUpdate={fetchBotData} />}
        {activeTab === "watchlist" && <BotWatchlist onUpdate={fetchBotData} />}
        {activeTab === "signals" && <BotSignals />}
        {activeTab === "trades" && <BotTrades />}
      </div>
    </div>
  );
}

export default BotDashboard;
