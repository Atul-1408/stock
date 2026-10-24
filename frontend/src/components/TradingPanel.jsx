import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShoppingCart, TrendingUp, TrendingDown, DollarSign, Activity, AlertCircle, CheckCircle2 } from 'lucide-react';
import api from '../utils/api';
import { useCurrency, getNativeCurrency } from '../contexts/CurrencyContext';
import { formatCurrency } from '../utils/currency';

const TradingPanel = ({ ticker, sentimentScore, sentimentLabel, currentPrice, onTradeSuccess, balance }) => {
    const { currency, convertPrice } = useCurrency();
    const [shares, setShares] = useState(1);
    const [action, setAction] = useState('BUY');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState({ type: '', text: '' });

    const totalCost = (shares * currentPrice).toFixed(2);
    const canAfford = action === 'BUY' ? balance >= totalCost : true;

    const handleTrade = async () => {
        if (shares <= 0) return;
        setLoading(true);
        setMessage({ type: '', text: '' });

        try {
            const response = await api.post('/trade', {
                ticker,
                action,
                shares: parseFloat(shares),
                sentiment_score: sentimentScore,
                sentiment_label: sentimentLabel
            });

            setMessage({ type: 'success', text: response.data.message });
            if (onTradeSuccess) onTradeSuccess(response.data.data);
            setShares(1);
        } catch (err) {
            setMessage({ type: 'error', text: err.response?.data?.message || 'Trade failed.' });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (message.text) {
            const timer = setTimeout(() => setMessage({ type: '', text: '' }), 5000);
            return () => clearTimeout(timer);
        }
    }, [message]);

    if (!ticker) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-6 border-slate-200/50 dark:border-slate-800/50 bg-white dark:bg-slate-900/40 backdrop-blur-md shadow-xl transition-colors duration-400"
        >
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 transition-colors">
                    <ShoppingCart className="w-5 h-5 text-blue-500" />
                    Trade {ticker}
                </h3>
                <div className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2 transition-colors">
                    <DollarSign className="w-4 h-4" />
                    Balance: <span className="text-slate-900 dark:text-white font-bold transition-colors">{formatCurrency(balance, currency)}</span>
                </div>
            </div>

            <div className="flex p-1 bg-slate-100 dark:bg-slate-800/50 rounded-xl mb-6 transition-colors">
                <button
                    onClick={() => setAction('BUY')}
                    className={`flex-1 py-2 rounded-lg font-bold transition-all ${action === 'BUY'
                        ? 'bg-emerald-500 text-white shadow-lg'
                        : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                        }`}
                >
                    BUY
                </button>
                <button
                    onClick={() => setAction('SELL')}
                    className={`flex-1 py-2 rounded-lg font-bold transition-all ${action === 'SELL'
                        ? 'bg-rose-500 text-white shadow-lg'
                        : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                        }`}
                >
                    SELL
                </button>
            </div>

            <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-800 transition-colors">
                        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1 transition-colors">Current Price</p>
                        <p className="text-2xl font-black text-slate-900 dark:text-white transition-colors">
                            {formatCurrency(convertPrice(currentPrice, getNativeCurrency(ticker)), currency)}
                        </p>
                    </div>
                    <div className={`p-4 rounded-2xl border transition-all ${sentimentScore > 0
                        ? 'bg-emerald-500/5 border-emerald-500/20'
                        : sentimentScore < 0
                            ? 'bg-rose-500/5 border-rose-500/20'
                            : 'bg-slate-500/5 border-slate-500/20'
                        }`}>
                        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1 transition-colors">AI Sentiment</p>
                        <div className="flex items-center gap-2">
                            <Activity className={`w-4 h-4 ${sentimentScore > 0 ? 'text-emerald-500' : sentimentScore < 0 ? 'text-rose-500' : 'text-slate-500'}`} />
                            <p className={`text-lg font-bold transition-colors ${sentimentScore > 0 ? 'text-emerald-500' : sentimentScore < 0 ? 'text-rose-500' : 'text-slate-500'}`}>
                                {sentimentLabel || 'Neutral'}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="space-y-2">
                    <div className="flex justify-between items-center ml-1">
                        <label className="text-sm font-bold text-slate-600 dark:text-slate-400 transition-colors">Shares to {action.toLowerCase()}</label>
                        <span className="text-xs text-slate-500 dark:text-slate-500 transition-colors">Min: 0.01</span>
                    </div>
                    <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={shares}
                        onChange={(e) => setShares(e.target.value)}
                        className="w-full bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 rounded-xl py-4 px-6 text-xl font-black text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                    />
                </div>

                <div className="p-4 rounded-2xl bg-blue-500/5 border border-blue-500/10 transition-colors">
                    <div className="flex justify-between items-center">
                        <span className="text-slate-600 dark:text-slate-400 font-medium transition-colors">Estimated Total</span>
                        <span className={`text-xl font-black transition-colors ${!canAfford && action === 'BUY' ? 'text-rose-500' : 'text-slate-900 dark:text-white'}`}>
                            {formatCurrency(convertPrice(totalCost, getNativeCurrency(ticker)), currency)}
                        </span>
                    </div>
                    {!canAfford && action === 'BUY' && (
                        <p className="text-xs text-rose-500 mt-2 font-bold flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> Insufficient balance
                        </p>
                    )}
                </div>

                <button
                    onClick={handleTrade}
                    disabled={loading || !canAfford || shares <= 0}
                    className={`w-full py-4 rounded-xl font-black text-lg shadow-lg flex items-center justify-center gap-2 transition-all active:scale-95 ${action === 'BUY'
                        ? 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-emerald-500/20'
                        : 'bg-rose-500 hover:bg-rose-400 text-white shadow-rose-500/20'
                        } disabled:opacity-50 disabled:active:scale-100`}
                >
                    {loading ? (
                        <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        <>
                            {action === 'BUY' ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                            CONFIRM {action}
                        </>
                    )}
                </button>

                <AnimatePresence>
                    {message.text && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className={`p-4 rounded-xl border flex items-center gap-3 ${message.type === 'success'
                                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                                }`}
                        >
                            {message.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                            <p className="text-sm font-bold">{message.text}</p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

export default TradingPanel;
