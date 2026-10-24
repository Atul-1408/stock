import React, { useState, useEffect } from "react";
import {
  Bell,
  Trash2,
  ShieldAlert,
  CheckCircle,
  Clock,
  Zap,
  Plus,
  X,
  Radio,
  ToggleLeft,
  ToggleRight,
  Filter,
} from "lucide-react";
import { toast } from "react-toastify";
import api from "../utils/api";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [newAlert, setNewAlert] = useState({
    ticker: "",
    alert_type: "sentiment_drop",
    condition_operator: "below",
    threshold_value: -0.3,
    notification_method: "email",
  });

  const fetchAlerts = async () => {
    try {
      const [alertsRes, historyRes, botRes] = await Promise.all([
        api.get("/alerts").catch(() => ({ data: { alerts: [] } })),
        api.get("/alerts/history").catch(() => ({ data: { logs: [] } })),
        api.get("/alerts/bot").catch(() => ({ data: { alerts: [] } })),
      ]);

      const botLogs = (botRes.data?.alerts || []).map((b) => ({
        ...b,
        is_bot: true,
      }));

      const allHistory = [...(historyRes.data?.logs || []), ...botLogs].sort(
        (a, b) => new Date(b.triggered_at) - new Date(a.triggered_at)
      );

      setAlerts(alertsRes.data?.alerts || []);
      setHistory(allHistory);
    } catch (error) {
      console.error("Error fetching alerts:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const createAlert = async (e) => {
    e.preventDefault();
    if (!newAlert.ticker.trim()) return toast.error("Enter a valid stock ticker symbol");

    try {
      await api.post("/alerts", {
        ...newAlert,
        ticker: newAlert.ticker.toUpperCase().trim(),
      });
      toast.success(`Signal watcher deployed for ${newAlert.ticker.toUpperCase()}`);
      fetchAlerts();
      setShowForm(false);
      setNewAlert({
        ticker: "",
        alert_type: "sentiment_drop",
        condition_operator: "below",
        threshold_value: -0.3,
        notification_method: "email",
      });
    } catch (error) {
      toast.error("Failed to deploy alert rule");
    }
  };

  const deleteAlert = async (id) => {
    if (!window.confirm("Are you sure you want to delete this signal watcher?")) {
      return;
    }
    try {
      await api.delete(`/alerts/${id}`);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      toast.info("Alert watcher removed");
    } catch (error) {
      toast.error("Delete operation failed");
    }
  };

  const toggleAlert = async (alert) => {
    try {
      await api.put(`/alerts/${alert.id}/toggle`, { is_active: !alert.is_active });
      setAlerts(
        alerts.map((a) => (a.id === alert.id ? { ...a, is_active: !alert.is_active } : a))
      );
      toast.info(`Watcher ${!alert.is_active ? "activated" : "deactivated"}`);
    } catch (error) {
      toast.error("Toggle failed");
    }
  };

  const markRead = async (id) => {
    try {
      await api.put(`/alerts/history/${id}/read`);
      setHistory(history.map((h) => (h.id === id ? { ...h, was_read: 1 } : h)));
    } catch (error) {}
  };

  return (
    <div className="space-y-4 font-mono">
      {/* ── Header Bar ── */}
      <div className="terminal-card p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <Radio size={16} className="text-cyan-400 animate-pulse" />
          <span className="font-bold text-white tracking-wider text-sm">
            SIGNAL DISPATCH & WATCHERS
          </span>
          <span className="text-[10px] bg-cyan-500/10 text-cyan-400 px-1.5 py-0.5 rounded border border-cyan-500/20 font-bold">
            {alerts.length} ACTIVE RULES
          </span>
        </div>

        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 rounded bg-emerald-500 hover:bg-emerald-400 text-black font-bold flex items-center gap-1.5 transition-all text-xs"
        >
          {showForm ? <X size={13} /> : <Plus size={13} />}
          <span>{showForm ? "DISMISS FORM" : "DEPLOY WATCHER"}</span>
        </button>
      </div>

      {/* ── Form Modal / Drawer ── */}
      {showForm && (
        <form onSubmit={createAlert} className="terminal-card p-4 space-y-3 border-cyan-500/30 text-xs">
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <span className="font-bold text-white flex items-center gap-1.5">
              <ShieldAlert size={14} className="text-cyan-400" />
              CONFIGURE NEW SIGNAL RULE
            </span>
            <span className="text-[10px] text-slate-500">REAL-TIME MONITOR</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase mb-1 block">TICKER</label>
              <input
                type="text"
                placeholder="e.g. AAPL"
                value={newAlert.ticker}
                onChange={(e) => setNewAlert({ ...newAlert, ticker: e.target.value })}
                className="w-full bg-[#090e17] border border-white/10 rounded py-1.5 px-2.5 text-xs text-white uppercase font-bold focus:outline-none focus:border-cyan-500/50"
              />
            </div>

            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase mb-1 block">TRIGGER TYPE</label>
              <select
                value={newAlert.alert_type}
                onChange={(e) => setNewAlert({ ...newAlert, alert_type: e.target.value })}
                className="w-full bg-[#090e17] border border-white/10 rounded py-1.5 px-2.5 text-xs text-white focus:outline-none"
              >
                <option value="sentiment_drop">Sentiment Drop</option>
                <option value="sentiment_rise">Sentiment Rise</option>
                <option value="price_target">Price Target</option>
                <option value="news_alert">News Alert</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase mb-1 block">THRESHOLD</label>
              <input
                type="number"
                step="0.01"
                value={newAlert.threshold_value}
                onChange={(e) => setNewAlert({ ...newAlert, threshold_value: parseFloat(e.target.value) || 0 })}
                className="w-full bg-[#090e17] border border-white/10 rounded py-1.5 px-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/50"
              />
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                className="w-full py-2 rounded bg-emerald-500 hover:bg-emerald-400 text-black font-bold uppercase transition-all"
              >
                DEPLOY WATCHER
              </button>
            </div>
          </div>
        </form>
      )}

      {/* ── 2. Two-Column Terminal Ledger (Left: Rules / Right: Trigger Logs) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Active Rules List (5 Cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="terminal-card p-3.5">
            <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
              <span className="text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
                <Bell size={13} className="text-cyan-400" />
                ACTIVE WATCHERS ({alerts.length})
              </span>
              <span className="text-[10px] text-slate-500">STATE ENFORCEMENT</span>
            </div>

            {alerts.length > 0 ? (
              <div className="space-y-2">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="p-3 rounded bg-black/30 border border-white/5 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{alert.ticker}</span>
                        <span className="text-[10px] text-cyan-400 bg-cyan-500/10 px-1 py-0.2 rounded font-semibold">
                          {alert.alert_type}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1">
                        CONDITION: {alert.condition_operator || "below"} {alert.threshold_value}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleAlert(alert)}
                        className={`p-1 rounded text-xs ${
                          alert.is_active ? "text-emerald-400" : "text-slate-500"
                        }`}
                        title={alert.is_active ? "Deactivate" : "Activate"}
                      >
                        {alert.is_active ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                      </button>

                      <button
                        onClick={() => deleteAlert(alert.id)}
                        className="p-1 rounded text-slate-500 hover:text-coral-400 transition-colors"
                        title="Remove"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-slate-500">
                NO ACTIVE RULES · DEPLOY A WATCHER ABOVE
              </div>
            )}
          </div>
        </div>

        {/* Triggered Signals Audit History (7 Cols) */}
        <div className="lg:col-span-7 space-y-3">
          <div className="terminal-card p-3.5">
            <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
              <span className="text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
                <Clock size={13} className="text-emerald-400" />
                DISPATCHED SIGNAL LOGS ({history.length})
              </span>
              <span className="text-[10px] text-slate-500">AUDIT TRAIL</span>
            </div>

            {history.length > 0 ? (
              <div className="space-y-2 max-h-[520px] overflow-y-auto custom-scrollbar pr-1">
                {history.map((log, idx) => {
                  const timeStr = log.triggered_at ? log.triggered_at.slice(0, 19).replace("T", " ") : "—";
                  return (
                    <div
                      key={log.id || idx}
                      onClick={() => log.id && markRead(log.id)}
                      className={`p-3 rounded border text-xs cursor-pointer transition-colors ${
                        log.was_read
                          ? "bg-black/20 border-white/5 text-slate-400"
                          : "bg-white/5 border-white/10 text-slate-200"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1 text-[10px]">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-white">{log.ticker || "GLOBAL"}</span>
                          {log.is_bot && (
                            <span className="text-[9px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-1 py-0.2 rounded font-bold">
                              ALGO BOT
                            </span>
                          )}
                        </div>
                        <span className="text-slate-500 font-mono">{timeStr}</span>
                      </div>

                      <p className="text-xs text-slate-300 leading-relaxed font-sans">{log.message}</p>

                      {log.price && (
                        <div className="mt-1 text-[10px] text-slate-400 font-mono">
                          PRICE AT TRIGGER: ${Number(log.price).toFixed(2)}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-slate-500">
                NO SIGNALS DISPATCHED IN CURRENT SESSION
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
