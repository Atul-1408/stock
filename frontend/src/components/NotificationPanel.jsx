import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, X, Zap, Trash2, RefreshCw } from "lucide-react";
import api from "../utils/api";
import { toast } from "react-toastify";

const NotificationPanel = ({ isOpen, onClose }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen]);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await api.get("/alerts/bot");
      setNotifications(res.data.alerts || []);
    } catch (err) {
      console.error("Error fetching bot alerts", err);
    } finally {
      setLoading(false);
    }
  };

  const clearAll = async () => {
    if (!window.confirm("Clear all active alert signals from session queue?")) return;
    try {
      await api.delete("/alerts/bot-clear");
      setNotifications([]);
      toast.success("Signal queue cleared");
    } catch (err) {
      toast.error("Failed to clear signal queue");
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs z-[100]"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 240 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-sm bg-[#0c1322] border-l border-terminal-800 shadow-2xl z-[101] flex flex-col font-mono"
          >
            {/* Header */}
            <div className="p-4 border-b border-terminal-800 flex justify-between items-center bg-terminal-950/60">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 bg-terminal-cyan/10 border border-terminal-cyan/30 rounded text-terminal-cyan">
                  <Bell className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                    Signal Telemetry
                  </h3>
                  <p className="text-2xs text-slate-400 uppercase tracking-wider">
                    {notifications.length} Incoming Dispatch{notifications.length === 1 ? "" : "es"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="p-1.5 text-slate-400 hover:text-terminal-coral hover:bg-terminal-coral/10 rounded transition-colors"
                    title="Purge notifications"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="p-1.5 rounded hover:bg-terminal-800 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Notifications Stream */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {loading && notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-slate-400 gap-2">
                  <RefreshCw className="w-5 h-5 text-terminal-cyan animate-spin" />
                  <p className="text-2xs uppercase tracking-wider">Syncing Signal Telemetry...</p>
                </div>
              ) : notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-center px-4">
                  <Zap className="w-8 h-8 text-terminal-800 mb-2" />
                  <p className="text-xs font-bold text-slate-400 uppercase">Queue Clear</p>
                  <p className="text-2xs text-slate-400 mt-1 font-sans">
                    Autonomous scanner continuously monitors threshold triggers across active markets.
                  </p>
                </div>
              ) : (
                notifications.map((notif) => {
                  const isUrgent =
                    notif.alert_type === "urgent_signal" || notif.message?.includes("URGENT");
                  const isTrade = notif.alert_type === "trade_signal";

                  return (
                    <div
                      key={notif.id}
                      className={`p-3 rounded border text-xs transition-colors ${
                        isUrgent
                          ? "bg-terminal-coral/10 border-terminal-coral/30"
                          : isTrade
                          ? "bg-terminal-emerald/10 border-terminal-emerald/30"
                          : "bg-terminal-950/60 border-terminal-800 hover:border-terminal-700"
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isUrgent
                                ? "bg-terminal-coral animate-pulse"
                                : isTrade
                                ? "bg-terminal-emerald"
                                : "bg-terminal-cyan"
                            }`}
                          />
                          <span className="text-2xs text-slate-400 uppercase">
                            {new Date(notif.triggered_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit"
                            })}
                          </span>
                        </div>

                        {notif.ticker && notif.ticker !== "GLOBAL" && (
                          <span
                            className={`px-1.5 py-0.2 text-2xs font-bold rounded ${
                              isUrgent
                                ? "badge-negative"
                                : isTrade
                                ? "badge-positive"
                                : "badge-cyan"
                            }`}
                          >
                            {notif.ticker}
                          </span>
                        )}
                      </div>

                      <p className="text-2xs text-slate-200 leading-relaxed font-sans whitespace-pre-line">
                        {notif.message?.replace(/\*\*/g, "")}
                      </p>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-terminal-800 bg-terminal-950/60 text-center text-2xs uppercase tracking-wider text-slate-400">
              Live Signal Telemetry Dispatch
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default NotificationPanel;
