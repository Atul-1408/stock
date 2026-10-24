import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, TrendingUp, TrendingDown, RefreshCw, BarChart3, Globe, ChevronDown, X } from 'lucide-react';
import api from '../utils/api';
import { useCurrency } from '../contexts/CurrencyContext';
import { formatCurrency, formatMarketCap } from '../utils/currency';
import OrderWindow from '../components/OrderWindow';
import OrdersPositions from '../components/OrdersPositions';

const MarketWatch = () => {
    const { currency } = useCurrency();
    const [stocks, setStocks] = useState([]);
    const [indices, setIndices] = useState([]);
    const [exchanges, setExchanges] = useState([]);
    const [sectors, setSectors] = useState([]);
    const [totalStocks, setTotalStocks] = useState(0);
    const [loading, setLoading] = useState(true);

    const [search, setSearch] = useState('');
    const [exchange, setExchange] = useState('all');
    const [sector, setSector] = useState('all');
    const [selectedStock, setSelectedStock] = useState(null);
    const [orderSide, setOrderSide] = useState('BUY');

    const fetchData = useCallback(async () => {
        try {
            const { data } = await api.get('/market/watch', {
                params: { exchange, sector, search, limit: 50, currency }
            });
            setStocks(data.stocks || []);
            setIndices(data.indices || []);
            setExchanges(data.exchanges || []);
            setSectors(data.sectors || []);
            setTotalStocks(data.total || 0);
        } catch (err) {
            console.error('Market watch error:', err);
        } finally {
            setLoading(false);
        }
    }, [exchange, sector, search, currency]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 15000);
        return () => clearInterval(interval);
    }, [fetchData]);

    const formatVolume = (vol) => {
        if (!vol) return '—';
        if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
        if (vol >= 1e3) return `${(vol / 1e3).toFixed(1)}K`;
        return vol.toLocaleString();
    };

    const openOrder = (stock, side) => {
        setSelectedStock(stock);
        setOrderSide(side);
    };

    // Use display_currency from API (converted) or fallback to selected currency
    const displayCurrency = currency;

    return (
        <div className="space-y-6">
            {/* ── Market Indices Ticker ── */}
            {indices.length > 0 && (
                <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
                    {indices.map(idx => {
                        const isUp = (idx.change_pct || 0) >= 0;
                        return (
                            <div key={idx.index_name} className="flex-shrink-0 bg-white/5 dark:bg-slate-800/50 backdrop-blur-sm border border-white/10 rounded-2xl px-5 py-3 min-w-[180px]">
                                <div className="text-xs text-slate-500 dark:text-gray-400 font-semibold mb-1">{idx.display_name || idx.index_name}</div>
                                <div className="flex items-center gap-2">
                                    <span className="text-lg font-bold text-slate-800 dark:text-white">{Number(idx.current_value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                    <span className={`flex items-center gap-0.5 text-sm font-bold ${isUp ? 'text-emerald-500' : 'text-red-500'}`}>
                                        {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                                        {Math.abs(idx.change_pct || 0).toFixed(2)}%
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* ── Filters Bar ── */}
            <div className="bg-white/5 dark:bg-slate-800/50 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="relative flex-1 min-w-[200px]">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Search stocks by symbol or name..."
                            className="w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-slate-800 dark:text-white placeholder-slate-500 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                        />
                    </div>

                    <div className="relative">
                        <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <select
                            value={exchange}
                            onChange={e => setExchange(e.target.value)}
                            className="bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl py-2.5 pl-10 pr-8 text-sm text-slate-800 dark:text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 cursor-pointer"
                        >
                            <option value="all">All Exchanges</option>
                            {exchanges.map(ex => <option key={ex} value={ex}>{ex}</option>)}
                        </select>
                        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                    </div>

                    <div className="relative">
                        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <select
                            value={sector}
                            onChange={e => setSector(e.target.value)}
                            className="bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl py-2.5 pl-10 pr-8 text-sm text-slate-800 dark:text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 cursor-pointer"
                        >
                            <option value="all">All Sectors</option>
                            {sectors.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                    </div>

                    <button onClick={fetchData} className="p-2.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-500 dark:text-blue-400 rounded-xl transition-colors" title="Refresh">
                        <RefreshCw className="w-4 h-4" />
                    </button>

                    <div className="text-xs text-slate-500 dark:text-gray-500 font-bold">
                        {totalStocks.toLocaleString()} stocks · <span className="text-blue-500 dark:text-blue-400">{displayCurrency}</span>
                    </div>
                </div>
            </div>

            {/* ── Main Content: Stock Table + Order Window ── */}
            <div className="flex gap-6">
                <div className="flex-1 bg-white/5 dark:bg-slate-800/30 backdrop-blur-sm border border-white/10 rounded-2xl overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-white/10 dark:border-slate-800">
                                    <th className="text-left py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">Symbol</th>
                                    <th className="text-left py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">Company</th>
                                    <th className="text-left py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">Exchange</th>
                                    <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">LTP ({displayCurrency})</th>
                                    <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">Change</th>
                                    <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">Volume</th>
                                    <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">Mkt Cap</th>
                                    <th className="text-center py-3 px-4 text-slate-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr><td colSpan="8" className="text-center py-16 text-gray-400">
                                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                                        Loading market data...
                                    </td></tr>
                                ) : stocks.length === 0 ? (
                                    <tr><td colSpan="8" className="text-center py-16 text-gray-400">
                                        No stocks found. Run the data importer first.
                                    </td></tr>
                                ) : stocks.map((stock, i) => {
                                    const isUp = (stock.change_pct || 0) >= 0;
                                    const dc = stock.display_currency || displayCurrency;
                                    return (
                                        <tr key={stock.symbol} className={`border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'} dark:bg-transparent`}>
                                            <td className="py-3 px-4">
                                                <span className="inline-flex items-center justify-center px-2.5 py-1 bg-blue-500/10 text-blue-500 dark:text-blue-400 rounded-lg text-xs font-bold tracking-wide">
                                                    {stock.symbol.replace('.NS', '')}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-slate-800 dark:text-white font-medium max-w-[200px] truncate">{stock.company_name}</td>
                                            <td className="py-3 px-4">
                                                <span className="text-xs font-bold text-slate-500 dark:text-gray-400 uppercase">{stock.exchange}</span>
                                            </td>
                                            <td className="py-3 px-4 text-right">
                                                <span className="text-slate-800 dark:text-white font-bold">{formatCurrency(stock.last_price, dc)}</span>
                                            </td>
                                            <td className="py-3 px-4 text-right">
                                                <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-lg ${isUp ? 'text-emerald-500 bg-emerald-500/10' : 'text-red-500 bg-red-500/10'
                                                    }`}>
                                                    {isUp ? '▲' : '▼'} {Math.abs(stock.change_pct || 0).toFixed(2)}%
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-right text-slate-600 dark:text-gray-300">{formatVolume(stock.volume)}</td>
                                            <td className="py-3 px-4 text-right text-slate-600 dark:text-gray-300">{formatMarketCap(stock.market_cap, dc)}</td>
                                            <td className="py-3 px-4">
                                                <div className="flex justify-center gap-1.5">
                                                    <button
                                                        onClick={() => openOrder(stock, 'BUY')}
                                                        className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-xs font-bold rounded-lg transition-colors"
                                                    >B</button>
                                                    <button
                                                        onClick={() => openOrder(stock, 'SELL')}
                                                        className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-bold rounded-lg transition-colors"
                                                    >S</button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>

                {selectedStock && (
                    <div className="w-[340px] flex-shrink-0">
                        <OrderWindow
                            stock={selectedStock}
                            side={orderSide}
                            onClose={() => setSelectedStock(null)}
                            onOrderPlaced={fetchData}
                        />
                    </div>
                )}
            </div>

            <OrdersPositions />
        </div>
    );
};

export default MarketWatch;
