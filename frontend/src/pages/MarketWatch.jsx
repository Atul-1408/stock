import React, { useState, useEffect, useCallback } from "react";
import {
  Search,
  Filter,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  BarChart3,
  Globe,
  SlidersHorizontal,
  ChevronDown,
  X,
} from "lucide-react";
import api from "../utils/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { formatCurrency, formatMarketCap } from "../utils/currency";
import OrderWindow from "../components/OrderWindow";
import OrdersPositions from "../components/OrdersPositions";

export default function MarketWatch() {
  const { currency } = useCurrency();
  const [stocks, setStocks] = useState([]);
  const [indices, setIndices] = useState([]);
  const [exchanges, setExchanges] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [totalStocks, setTotalStocks] = useState(0);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");
  const [exchange, setExchange] = useState("all");
  const [sector, setSector] = useState("all");
  const [selectedStock, setSelectedStock] = useState(null);
  const [orderSide, setOrderSide] = useState("BUY");

  const fetchData = useCallback(async () => {
    try {
      const { data } = await api.get("/market/watch", {
        params: { exchange, sector, search, limit: 50, currency },
      });
      setStocks(data.stocks || []);
      setIndices(data.indices || []);
      setExchanges(data.exchanges || []);
      setSectors(data.sectors || []);
      setTotalStocks(data.total || 0);
    } catch (err) {
      console.error("Market watch error:", err);
    } finally {
      setLoading(false);
    }
  }, [exchange, sector, search, currency]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const formatVolume = (vol) => {
    if (!vol) return "—";
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(1)}K`;
    return vol.toLocaleString();
  };

  const openOrder = (stock, side) => {
    setSelectedStock(stock);
    setOrderSide(side);
  };

  return (
    <div className="space-y-4 font-mono">
      {/* ── 1. Macro Market Indices Banner ── */}
      {indices.length > 0 && (
        <div className="flex gap-2.5 overflow-x-auto no-scrollbar pb-1">
          {indices.map((idx) => {
            const isUp = (idx.change_pct || 0) >= 0;
            return (
              <div
                key={idx.index_name}
                className="terminal-card px-3 py-2 flex-shrink-0 min-w-[160px] flex items-center justify-between text-xs"
              >
                <div>
                  <div className="text-[10px] text-slate-400 font-semibold">{idx.display_name || idx.index_name}</div>
                  <div className="text-sm font-bold text-white mt-0.5">
                    {Number(idx.current_value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}
                  </div>
                </div>
                <div className={`text-[11px] font-bold flex items-center gap-0.5 ${isUp ? "text-emerald-400" : "text-coral-400"}`}>
                  {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                  {isUp ? "+" : ""}{Number(idx.change_pct || 0).toFixed(2)}%
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── 2. Scanner & Filter Bar ── */}
      <div className="terminal-card p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 w-3.5 h-3.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by symbol, company name..."
            className="w-full bg-[#090e17] border border-white/10 rounded py-1.5 pl-8 pr-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        {/* Exchange Filter */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-400 font-bold uppercase">EXCHANGE:</span>
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="bg-[#090e17] border border-white/10 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none"
          >
            <option value="all">ALL EXCHANGES ({totalStocks})</option>
            {exchanges.map((ex) => (
              <option key={ex} value={ex}>{ex}</option>
            ))}
          </select>
        </div>

        {/* Sector Filter */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-400 font-bold uppercase">SECTOR:</span>
          <select
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            className="bg-[#090e17] border border-white/10 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none"
          >
            <option value="all">ALL SECTORS</option>
            {sectors.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {/* Manual Refresh */}
        <button
          onClick={fetchData}
          disabled={loading}
          className="p-1.5 rounded bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-colors"
          title="Refresh Universe Feed"
        >
          <RefreshCw size={13} className={loading ? "animate-spin text-cyan-400" : ""} />
        </button>
      </div>

      {/* ── 3. Stock Universe Table & Order Execution Drawer ── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Market Table (Left 8 or 12 Cols depending on Order Window state) */}
        <div className={selectedStock ? "xl:col-span-8 space-y-4" : "xl:col-span-12 space-y-4"}>
          <div className="terminal-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/5 text-[10px] text-slate-400 uppercase bg-[#080d16]">
                    <th className="py-2.5 px-3 font-semibold">SYMBOL</th>
                    <th className="py-2.5 px-3 font-semibold">COMPANY</th>
                    <th className="py-2.5 px-3 font-semibold">EXCHANGE</th>
                    <th className="py-2.5 px-3 font-semibold text-right">LTP</th>
                    <th className="py-2.5 px-3 font-semibold text-right">CHANGE</th>
                    <th className="py-2.5 px-3 font-semibold text-right">HIGH</th>
                    <th className="py-2.5 px-3 font-semibold text-right">LOW</th>
                    <th className="py-2.5 px-3 font-semibold text-right">VOLUME</th>
                    <th className="py-2.5 px-3 font-semibold text-center">TRADE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {stocks.length > 0 ? (
                    stocks.map((stock) => {
                      const isUp = (stock.change_pct || 0) >= 0;
                      const isSelected = selectedStock?.symbol === stock.symbol;

                      return (
                        <tr
                          key={stock.symbol}
                          className={`hover:bg-white/5 transition-colors ${
                            isSelected ? "bg-white/10" : ""
                          }`}
                        >
                          <td className="py-2.5 px-3 font-bold text-white">{stock.symbol}</td>
                          <td className="py-2.5 px-3 text-slate-300 truncate max-w-[180px]">{stock.company_name}</td>
                          <td className="py-2.5 px-3">
                            <span className="text-[10px] text-cyan-400 bg-cyan-500/10 px-1 py-0.5 rounded border border-cyan-500/20 font-bold">
                              {stock.exchange}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-white">
                            {stock.last_price != null ? `$${Number(stock.last_price).toFixed(2)}` : "—"}
                          </td>
                          <td className={`py-2.5 px-3 text-right font-bold ${isUp ? "text-emerald-400" : "text-coral-400"}`}>
                            {stock.change_pct != null
                              ? `${isUp ? "+" : ""}${Number(stock.change_pct).toFixed(2)}%`
                              : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-400 font-mono">
                            {stock.high_price != null ? `$${Number(stock.high_price).toFixed(2)}` : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-400 font-mono">
                            {stock.low_price != null ? `$${Number(stock.low_price).toFixed(2)}` : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-400 font-mono">
                            {formatVolume(stock.volume)}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <div className="inline-flex gap-1">
                              <button
                                onClick={() => openOrder(stock, "BUY")}
                                className="px-2 py-0.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-bold text-[10px] border border-emerald-500/20"
                              >
                                BUY
                              </button>
                              <button
                                onClick={() => openOrder(stock, "SELL")}
                                className="px-2 py-0.5 rounded bg-coral-500/10 hover:bg-coral-500/20 text-coral-400 font-bold text-[10px] border border-coral-500/20"
                              >
                                SELL
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="9" className="py-12 text-center text-slate-500">
                        {loading ? "SCANNING STOCK UNIVERSE..." : "NO MATCHING ASSETS FOUND"}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Integrated Orders & Positions Ledger */}
          <OrdersPositions />
        </div>

        {/* Slide-in Order Window (Right 4 Cols when active) */}
        {selectedStock && (
          <div className="xl:col-span-4 sticky top-16">
            <OrderWindow
              stock={selectedStock}
              side={orderSide}
              onClose={() => setSelectedStock(null)}
              onOrderPlaced={() => {
                fetchData();
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
