import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { ChevronRight, Globe, Zap, Search } from "lucide-react";
import { STOCKS } from "../constants/stocks";

function StockSidebar({ activeTicker, onSelect }) {
    const [search, setSearch] = useState("");
    const [activeRegion, setActiveRegion] = useState("India");

    const filteredStocks = useMemo(() => {
        const term = search.toLowerCase();
        const result = {};
        Object.entries(STOCKS).forEach(([region, stocks]) => {
            if (region !== activeRegion && !search) return; // Only filter if searching, otherwise show active region
            const matched = stocks.filter(s =>
                s.ticker.toLowerCase().includes(term) ||
                s.name.toLowerCase().includes(term)
            );
            if (matched.length > 0) result[region] = matched;
        });
        return result;
    }, [search, activeRegion]);

    return (
        <aside className="w-full lg:w-72 flex-shrink-0">
            <div className="sticky top-10 space-y-6">
                {/* Search & Tabs Header */}
                <div className="space-y-4 px-2">
                    <div className="flex items-center gap-2 text-accent font-bold text-sm tracking-widest uppercase">
                        <Globe className="w-4 h-4" /> Global Markets
                    </div>

                    {/* Region Tabs */}
                    <div className="flex p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/50">
                        {["India", "USA", "Crypto"].map((region) => (
                            <button
                                key={region}
                                onClick={() => setActiveRegion(region)}
                                className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all duration-300 relative ${activeRegion === region
                                    ? "text-accent"
                                    : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                                    }`}
                            >
                                {region}
                                {activeRegion === region && (
                                    <motion.div
                                        layoutId="activeTab"
                                        className="absolute inset-0 bg-white dark:bg-slate-700 shadow-sm rounded-lg -z-10"
                                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                    />
                                )}
                            </button>
                        ))}
                    </div>

                    <div className="relative group">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-accent transition-colors" />
                        <input
                            type="text"
                            placeholder={`Search ${activeRegion} stocks...`}
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-700/50 rounded-xl text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all font-medium"
                        />
                    </div>
                </div>

                <div className="max-h-[calc(100vh-320px)] overflow-y-auto space-y-6 px-2 custom-scrollbar pr-1">
                    {Object.entries(filteredStocks).length === 0 ? (
                        <div className="text-center py-10 px-4">
                            <p className="text-xs text-slate-500 font-medium italic">No stocks found in {activeRegion} matching "{search}"</p>
                        </div>
                    ) : Object.entries(filteredStocks).map(([region, stocks]) => (
                        <div key={region} className="space-y-3">
                            <h3 className="px-3 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] sticky top-0 bg-transparent py-1 flex justify-between items-center">
                                {region}
                                <span className="text-[10px] font-mono normal-case tracking-normal opacity-60">({stocks.length})</span>
                            </h3>
                            <div className="space-y-0.5">
                                {stocks.map((stock) => {
                                    const isActive = activeTicker === stock.ticker;
                                    return (
                                        <button
                                            key={stock.ticker}
                                            onClick={() => onSelect(stock.ticker)}
                                            className={`w-full group flex items-center justify-between px-3 py-2 rounded-xl transition-all duration-200 ${isActive
                                                ? "bg-accent/10 border-accent/20 text-accent font-bold"
                                                : "hover:bg-slate-100 dark:hover:bg-slate-800/40 text-slate-600 dark:text-slate-400 border-transparent"
                                                } border`}
                                        >
                                            <div className="flex items-center gap-3 overflow-hidden">
                                                <div className={`w-7 h-7 flex-shrink-0 rounded flex items-center justify-center text-[9px] font-black transition-colors ${isActive ? "bg-accent text-slate-900" : "bg-slate-200 dark:bg-slate-800 text-slate-500"
                                                    }`}>
                                                    {stock.ticker.split('.')[0].substring(0, 3)}
                                                </div>
                                                <div className="text-left truncate">
                                                    <div className="text-[13px] tracking-tight truncate leading-tight">{stock.name}</div>
                                                    <div className="text-[9px] opacity-60 font-mono leading-none">{stock.ticker}</div>
                                                </div>
                                            </div>
                                            {isActive ? (
                                                <Zap className="w-3 h-3 fill-accent" />
                                            ) : (
                                                <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="card p-4 mx-2 bg-gradient-to-br from-accent/5 to-blue-500/5 border-dashed">
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                        Analysis is powered by AI. Historical data is refreshed every few hours.
                    </p>
                </div>
            </div>
        </aside>
    );
}

export default StockSidebar;
