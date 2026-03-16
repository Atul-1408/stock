import React from 'react';
import { motion } from 'framer-motion';
import { History, ArrowUpRight, ArrowDownLeft, Clock, Activity } from 'lucide-react';

const TransactionHistory = ({ data, loading }) => {
    if (loading) return (
        <div className="animate-pulse space-y-4 py-10">
            <div className="h-8 bg-slate-200 dark:bg-slate-800 rounded-lg w-1/3"></div>
            {[1, 2, 3].map(i => <div key={i} className="h-20 bg-slate-200 dark:bg-slate-800 rounded-xl"></div>)}
        </div>
    );

    if (!data || data.length === 0) return null;

    return (
        <div className="mt-12">
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-slate-100 dark:bg-slate-800/80 rounded-lg transition-colors">
                    <History className="w-5 h-5 text-slate-500" />
                </div>
                <h3 className="text-xl font-black text-slate-900 dark:text-white transition-colors">Recent Activity</h3>
            </div>

            <div className="space-y-3">
                {data.map((tx) => (
                    <motion.div
                        initial={{ opacity: 0, x: -10 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        key={tx.id}
                        className="flex items-center justify-between p-4 bg-white dark:bg-slate-900/40 border border-slate-200/50 dark:border-slate-800/50 rounded-2xl transition-all hover:bg-slate-50 dark:hover:bg-slate-800/20 group cursor-default"
                    >
                        <div className="flex items-center gap-4">
                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${tx.action === 'BUY'
                                    ? 'bg-emerald-500/10 text-emerald-500 group-hover:bg-emerald-500 group-hover:text-white'
                                    : 'bg-rose-500/10 text-rose-500 group-hover:bg-rose-500 group-hover:text-white'
                                }`}>
                                {tx.action === 'BUY' ? <ArrowUpRight className="w-6 h-6" /> : <ArrowDownLeft className="w-6 h-6" />}
                            </div>

                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="font-black text-slate-900 dark:text-white transition-colors">{tx.ticker}</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-black uppercase ${tx.action === 'BUY' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'
                                        }`}>
                                        {tx.action}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3 mt-1">
                                    <div className="flex items-center gap-1 text-[11px] font-bold text-slate-500 dark:text-slate-500 transition-colors">
                                        <Clock className="w-3 h-3" />
                                        {new Date(tx.timestamp).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                                    </div>
                                    {tx.sentiment_label && (
                                        <div className="flex items-center gap-1 text-[11px] font-bold transition-colors text-slate-500">
                                            <Activity className={`w-3 h-3 ${tx.sentiment_score > 0 ? 'text-emerald-500' : tx.sentiment_score < 0 ? 'text-rose-500' : 'text-slate-500'}`} />
                                            Score: {tx.sentiment_score.toFixed(2)}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="text-right">
                            <p className="font-black text-slate-900 dark:text-white transition-colors">${tx.total_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                            <p className="text-xs font-bold text-slate-500 dark:text-slate-500 transition-colors">{tx.shares} shares @ ${tx.price_per_share.toFixed(2)}</p>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
};

export default TransactionHistory;
