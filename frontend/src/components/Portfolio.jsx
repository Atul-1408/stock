import React from 'react';
import { motion } from 'framer-motion';
import { Briefcase, TrendingUp, TrendingDown, LayoutGrid, Layers } from 'lucide-react';

const Portfolio = ({ data, loading }) => {
    if (loading) return (
        <div className="animate-pulse space-y-4">
            <div className="h-10 bg-slate-200 dark:bg-slate-800 rounded-xl"></div>
            <div className="h-40 bg-slate-200 dark:bg-slate-800 rounded-2xl"></div>
        </div>
    );

    if (!data || data.holdings.length === 0) return (
        <div className="card p-8 border-dashed border-2 bg-slate-500/5 dark:bg-slate-400/5 text-center transition-colors">
            <Briefcase className="w-10 h-10 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">No Holdings Yet</h3>
            <p className="text-slate-500 dark:text-slate-400">Your portfolio is empty. Make your first trade to see it here.</p>
        </div>
    );

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6"
        >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="card p-6 border-slate-200/50 dark:border-slate-800/50 bg-white dark:bg-slate-900/40 backdrop-blur-md transition-colors">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 transition-colors">Total Market Value</p>
                    <div className="flex items-end gap-2">
                        <p className="text-3xl font-black text-slate-900 dark:text-white transition-colors">
                            ${data.total_market_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                        <Layers className="w-5 h-5 text-blue-500 mb-2" />
                    </div>
                </div>
                <div className="card p-6 border-slate-200/50 dark:border-slate-800/50 bg-white dark:bg-slate-900/40 backdrop-blur-md transition-colors">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 transition-colors">Total P&L</p>
                    <div className="flex items-center gap-3">
                        <p className={`text-3xl font-black transition-colors ${data.total_pnl >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {data.total_pnl >= 0 ? '+' : ''}${data.total_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                        {data.total_pnl >= 0 ? <TrendingUp className="w-6 h-6 text-emerald-500" /> : <TrendingDown className="w-6 h-6 text-rose-500" />}
                    </div>
                </div>
            </div>

            <div className="card overflow-hidden border-slate-200/50 dark:border-slate-800/50 bg-white dark:bg-slate-900/40 backdrop-blur-md transition-colors">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50/50 dark:bg-slate-800/20 border-b border-slate-200/50 dark:border-slate-800/50 transition-colors">
                                <th className="px-6 py-4 text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider transition-colors">Stock</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider transition-colors">Shares</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider transition-colors">Avg Price</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider transition-colors">Current</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider transition-colors">Market Value</th>
                                <th className="px-6 py-4 text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider transition-colors text-right">P&L</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50 transition-colors">
                            {data.holdings.map((holding) => (
                                <tr key={holding.ticker} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/10 transition-colors cursor-default">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center font-bold text-blue-500 text-xs transition-colors">
                                                {holding.ticker[0]}
                                            </div>
                                            <span className="font-black text-slate-800 dark:text-slate-200 transition-colors">{holding.ticker}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 font-bold text-slate-700 dark:text-slate-300 transition-colors">{holding.shares}</td>
                                    <td className="px-6 py-4 font-bold text-slate-600 dark:text-slate-400 transition-colors">${holding.avg_price.toFixed(2)}</td>
                                    <td className="px-6 py-4 font-bold text-slate-900 dark:text-white transition-colors">${holding.current_price.toFixed(2)}</td>
                                    <td className="px-6 py-4 font-black text-slate-800 dark:text-slate-200 transition-colors">${holding.market_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                                    <td className="px-6 py-4 text-right">
                                        <div className={`inline-flex items-center gap-1.5 font-black ${holding.pnl >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                            {holding.pnl >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                            {holding.pnl >= 0 ? '+' : ''}{holding.pnl_percent.toFixed(2)}%
                                        </div>
                                        <p className={`text-[10px] font-bold mt-0.5 ${holding.pnl >= 0 ? 'text-emerald-500/60' : 'text-rose-500/60'}`}>
                                            ${Math.abs(holding.pnl).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                        </p>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </motion.div>
    );
};

export default Portfolio;
