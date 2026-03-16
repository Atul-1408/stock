import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, X, Zap, Info, AlertTriangle, CheckCircle, Trash2 } from 'lucide-react';
import api from '../utils/api';
import { toast } from 'react-toastify';

const NotificationPanel = ({ isOpen, onClose }) => {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchNotifications();
            // Mark unread conceptually? Since it's global, we just show them.
        }
    }, [isOpen]);

    const fetchNotifications = async () => {
        setLoading(true);
        try {
            const res = await api.get('/alerts/bot');
            setNotifications(res.data.alerts);
        } catch (err) {
            console.error("Error fetching bot alerts", err);
        } finally {
            setLoading(false);
        }
    };

    const clearAll = async () => {
        if (!window.confirm("Are you sure you want to clear all bot notifications?")) return;
        try {
            await api.delete('/alerts/bot-clear');
            setNotifications([]);
            toast.success("Notifications cleared");
        } catch (err) {
            toast.error("Failed to clear notifications");
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
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100]"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="fixed right-0 top-10 bottom-0 w-full max-w-sm bg-white dark:bg-[#0F1117] shadow-2xl z-[101] flex flex-col"
                    >
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-accent/10 rounded-lg">
                                    <Bell className="w-5 h-5 text-accent" />
                                </div>
                                <div>
                                    <h3 className="font-black text-slate-900 dark:text-white">Bot Intelligence</h3>
                                    <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Automated Signals</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {notifications.length > 0 && (
                                    <button 
                                        onClick={clearAll}
                                        className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 rounded-lg transition-all"
                                        title="Clear All"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                )}
                                <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                                    <X className="w-5 h-5 text-slate-400" />
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
                            {loading && notifications.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-40 text-slate-400">
                                    <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mb-4" />
                                    <p className="text-sm font-bold uppercase tracking-widest">Syncing Signals...</p>
                                </div>
                            ) : notifications.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-60 text-center px-6">
                                    <Zap className="w-12 h-12 text-slate-200 dark:text-slate-800 mb-4" />
                                    <p className="text-slate-500 font-bold">No signals detected by the bot yet.</p>
                                    <p className="text-xs text-slate-400 mt-2">The AI bot scans the market every minute for high-probability setups.</p>
                                </div>
                            ) : (
                                notifications.map((notif) => {
                                    const isUrgent = notif.alert_type === 'urgent_signal' || notif.message.includes('URGENT');
                                    const isTrade = notif.alert_type === 'trade_signal';
                                    
                                    return (
                                        <div 
                                            key={notif.id}
                                            className={`p-4 rounded-2xl border transition-all group ${
                                                isUrgent ? 'bg-rose-500/5 border-rose-500/20 hover:border-rose-500/40' : 
                                                isTrade ? 'bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40' :
                                                'bg-slate-50 dark:bg-slate-800/40 border-slate-100 dark:border-slate-700/50 hover:border-accent/30'
                                            }`}
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="flex items-center gap-2">
                                                    <span className={`w-2 h-2 rounded-full ${
                                                        isUrgent ? 'bg-rose-500 animate-pulse' : 
                                                        isTrade ? 'bg-emerald-500' : 
                                                        'bg-accent'
                                                    }`} />
                                                    <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">
                                                        {new Date(notif.triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                    </span>
                                                </div>
                                                {notif.ticker && notif.ticker !== 'GLOBAL' && (
                                                    <span className={`px-2 py-0.5 text-[10px] font-black rounded-md ${
                                                        isUrgent ? 'bg-rose-500/10 text-rose-500' :
                                                        isTrade ? 'bg-emerald-500/10 text-emerald-500' :
                                                        'bg-accent/10 text-accent'
                                                    }`}>
                                                        {notif.ticker}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                                                {notif.message.replace(/\*\*/g, '')}
                                            </p>
                                        </div>
                                    );
                                })
                            )}
                        </div>

                        <div className="p-4 bg-slate-50 dark:bg-slate-800/20 border-t border-slate-100 dark:border-slate-800">
                            <p className="text-[10px] text-center text-slate-500 font-bold uppercase tracking-widest">
                                Powered by Sovereign Intelligence AI
                            </p>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};

export default NotificationPanel;
