import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, Trash2, ShieldAlert, CheckCircle, Clock, Zap, Plus, X } from 'lucide-react';
import { toast } from 'react-toastify';
import api from '../utils/api';

const AlertsPage = () => {
    const [alerts, setAlerts] = useState([]);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);

    const [newAlert, setNewAlert] = useState({
        ticker: '',
        alert_type: 'sentiment_drop',
        condition_operator: 'below',
        threshold_value: -0.3,
        notification_method: 'email'
    });

    const fetchAlerts = async () => {
        try {
            const [alertsRes, historyRes, botRes] = await Promise.all([
                api.get('/alerts'),
                api.get('/alerts/history'),
                api.get('/alerts/bot')
            ]);
            
            // Merge history with bot alerts
            const botLogs = botRes.data.alerts.map(b => ({
                ...b,
                is_bot: true
            }));
            
            const allHistory = [...historyRes.data.logs, ...botLogs].sort((a, b) => 
                new Date(b.triggered_at) - new Date(a.triggered_at)
            );
            
            setAlerts(alertsRes.data.alerts);
            setHistory(allHistory);
        } catch (error) {
            console.error('Error fetching alerts:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();
    }, []);

    const createAlert = async (e) => {
        e.preventDefault();
        if (!newAlert.ticker) return toast.error("Please enter a stock ticker");

        try {
            await api.post('/alerts', newAlert);
            toast.success(`Alert for ${newAlert.ticker} created!`);
            fetchAlerts();
            setShowForm(false);
            setNewAlert({ ticker: '', alert_type: 'sentiment_drop', condition_operator: 'below', threshold_value: -0.3, notification_method: 'email' });
        } catch (error) {
            toast.error("Failed to create alert");
        }
    };

    const deleteAlert = async (id) => {
        try {
            await api.delete(`/alerts/${id}`);
            setAlerts(alerts.filter(a => a.id !== id));
            toast.info("Alert removed");
        } catch (error) {
            toast.error("Delete failed");
        }
    };

    const toggleAlert = async (alert) => {
        try {
            await api.put(`/alerts/${alert.id}/toggle`, { is_active: !alert.is_active });
            setAlerts(alerts.map(a => a.id === alert.id ? { ...a, is_active: !alert.is_active } : a));
        } catch (error) {
            toast.error("Toggle failed");
        }
    };

    const markRead = async (id) => {
        try {
            await api.put(`/alerts/history/${id}/read`);
            setHistory(history.map(h => h.id === id ? { ...h, was_read: 1 } : h));
        } catch (error) { }
    };

    if (loading && !alerts.length) return <div className="py-20 text-center animate-pulse text-slate-500">Loading your signal watchers...</div>;

    return (
        <div className="space-y-8 pb-20">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-black text-slate-900 dark:text-white flex items-center gap-3">
                        <Bell className="w-8 h-8 text-accent" /> Signal Central
                    </h2>
                    <p className="text-slate-500 mt-1">Configure automated triggers for market movements.</p>
                </div>
                <button
                    onClick={() => setShowForm(true)}
                    className="bg-accent hover:opacity-90 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-accent/20"
                >
                    <Plus className="w-5 h-5" /> New Alert
                </button>
            </div>

            <AnimatePresence>
                {showForm && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                    >
                        <form onSubmit={createAlert} className="card p-8 relative">
                            <button
                                type="button"
                                onClick={() => setShowForm(false)}
                                className="absolute top-4 right-4 text-slate-400 hover:text-slate-600"
                            >
                                <X className="w-5 h-5" />
                            </button>

                            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                                <ShieldAlert className="w-5 h-5 text-accent" /> Configure Trigger
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                                <div>
                                    <label className="text-xs font-black uppercase text-slate-500 mb-2 block">Ticker</label>
                                    <input
                                        type="text"
                                        placeholder="AAPL"
                                        className="w-full bg-slate-100 dark:bg-slate-800 border-none rounded-xl p-3 font-bold uppercase"
                                        value={newAlert.ticker}
                                        onChange={e => setNewAlert({ ...newAlert, ticker: e.target.value })}
                                    />
                                </div>

                                <div>
                                    <label className="text-xs font-black uppercase text-slate-500 mb-2 block">Type</label>
                                    <select
                                        className="w-full bg-slate-100 dark:bg-slate-800 border-none rounded-xl p-3 font-bold appearance-none"
                                        value={newAlert.alert_type}
                                        onChange={e => setNewAlert({ ...newAlert, alert_type: e.target.value })}
                                    >
                                        <option value="sentiment_drop">Sentiment Drop</option>
                                        <option value="sentiment_rise">Sentiment Rise</option>
                                        <option value="price_target">Price Target</option>
                                        <option value="news_alert">News Alert</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-xs font-black uppercase text-slate-500 mb-2 block">Threshold</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="w-full bg-slate-100 dark:bg-slate-800 border-none rounded-xl p-3 font-bold"
                                        value={newAlert.threshold_value}
                                        onChange={e => setNewAlert({ ...newAlert, threshold_value: parseFloat(e.target.value) })}
                                    />
                                </div>

                                <div className="flex items-end">
                                    <button
                                        type="submit"
                                        className="w-full bg-slate-900 dark:bg-white dark:text-gray-900 text-white p-3 rounded-xl font-black hover:opacity-90 transition-opacity"
                                    >
                                        Deploy Alert
                                    </button>
                                </div>
                            </div>
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Active Alerts List */}
                <div className="lg:col-span-2 space-y-4">
                    <h3 className="text-lg font-black uppercase tracking-wider text-slate-500 flex items-center gap-2">
                        <Zap className="w-4 h-4" /> Active Watchers
                    </h3>

                    {alerts.length === 0 ? (
                        <div className="card p-10 text-center">
                            <p className="text-slate-400 font-medium">No active alerts. Create one to stay ahead of the curve.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {alerts.map(alert => (
                                <motion.div
                                    layout
                                    key={alert.id}
                                    className={`card p-5 flex items-center justify-between border-l-4 ${alert.is_active ? 'border-accent' : 'border-slate-300 opacity-60'}`}
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center font-black text-lg">
                                            {alert.ticker}
                                        </div>
                                        <div>
                                            <h4 className="font-black text-slate-900 dark:text-white capitalize">
                                                {alert.alert_type.replace('_', ' ')}
                                            </h4>
                                            <p className="text-xs text-slate-500 font-bold uppercase tracking-tight">
                                                {alert.condition_operator || 'Value'} {alert.threshold_value} • via {alert.notification_method}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => toggleAlert(alert)}
                                            className={`px-3 py-1.5 rounded-lg text-xs font-black transition-colors ${alert.is_active ? 'bg-accent/10 text-accent' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'}`}
                                        >
                                            {alert.is_active ? 'ENABLED' : 'DISABLED'}
                                        </button>
                                        <button
                                            onClick={() => deleteAlert(alert.id)}
                                            className="p-2 text-rose-500 hover:bg-rose-500/10 rounded-lg transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Alert History */}
                <div className="space-y-4">
                    <h3 className="text-lg font-black uppercase tracking-wider text-slate-500 flex items-center gap-2">
                        <Clock className="w-4 h-4" /> Trigger Logs
                    </h3>
                    <div className="card flex flex-col divide-y divide-slate-100 dark:divide-slate-800 max-h-[600px] overflow-y-auto">
                        {history.length === 0 ? (
                            <div className="p-10 text-center text-slate-400 text-sm font-medium italic">No signals caught yet.</div>
                        ) : history.map(log => (
                            <div
                                key={log.id}
                                className={`p-4 hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors relative ${!log.was_read && !log.is_bot ? 'bg-accent/5' : ''}`}
                                onClick={() => !log.was_read && !log.is_bot && markRead(log.id)}
                            >
                                {!log.was_read && !log.is_bot && <div className="absolute top-4 right-4 w-2 h-2 bg-accent rounded-full"></div>}
                                {log.is_bot && <div className="absolute top-4 right-4"><Zap className="w-3 h-3 text-accent" /></div>}
                                <div className="flex justify-between items-start mb-1">
                                    <span className="text-[10px] font-black uppercase text-slate-400">
                                        {new Date(log.triggered_at).toLocaleDateString()} {new Date(log.triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                    <span className={`font-bold text-xs ${log.is_bot ? 'text-amber-500' : 'text-accent'}`}>
                                        {log.is_bot ? 'BOT SIGNAL' : log.ticker}
                                    </span>
                                </div>
                                <p className={`text-xs font-medium leading-relaxed ${log.is_bot ? 'text-slate-900 dark:text-white font-bold' : 'text-slate-700 dark:text-slate-300'}`}>
                                    {log.message.replace(/\*\*/g, '')}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AlertsPage;
