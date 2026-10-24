import React, { useState, useEffect, useCallback } from "react";
import {
  TrendingUp,
  TrendingDown,
  Globe2,
  Activity,
  Wallet,
  PieChart,
  RefreshCw,
  AlertCircle,
  Clock,
  Layers,
} from "lucide-react";
import { useCurrency, getNativeCurrency } from "../contexts/CurrencyContext";
import { formatCurrency } from "../utils/currency";
import api from "../utils/api";

import PriceChart from "../components/PriceChart";
import SentimentChart from "../components/SentimentChart";
import NewsFeed from "../components/NewsFeed";
import MarketMood from "../components/MarketMood";
import TradingPanel from "../components/TradingPanel";
import MarketBriefWidget from "../components/MarketBriefWidget";
import StockIntelligenceCard from "../components/StockIntelligenceCard";

const DEFAULT_TICKERS = [
  { symbol: "RELIANCE.NS", name: "Reliance Ind.", exchange: "NSE" },
  { symbol: "TCS.NS", name: "Tata Consultancy", exchange: "NSE" },
  { symbol: "HDFCBANK.NS", name: "HDFC Bank", exchange: "NSE" },
  { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ" },
  { symbol: "NVDA", name: "NVIDIA Corp.", exchange: "NASDAQ" },
  { symbol: "TSLA", name: "Tesla Inc.", exchange: "NASDAQ" },
];

export default function Dashboard() {
  const { currency, convertPrice } = useCurrency();

  const [activeSymbol, setActiveSymbol] = useState("AAPL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [indices, setIndices] = useState([]);
  const [tickerPrices, setTickerPrices] = useState({});
  const [sentiments, setSentiments] = useState([]);
  const [prices, setPrices] = useState([]);
  const [news, setNews] = useState([]);

  const [user, setUser] = useState(null);
  const [portfolio, setPortfolio] = useState({ holdings: [], total_market_value: 0, total_pnl: 0 });
  const [transactions, setTransactions] = useState([]);

  // Fetch macro market indices and user account data
  const fetchMarketContext = useCallback(async () => {
    try {
      const [indicesRes, userRes, portRes, transRes] = await Promise.all([
        api.get("/market/indices").catch(() => ({ data: { indices: [] } })),
        api.get("/auth/me").catch(() => ({ data: { user: null } })),
        api.get("/portfolio").catch(() => ({ data: { data: { holdings: [], total_market_value: 0, total_pnl: 0 } } })),
        api.get("/transactions?limit=6").catch(() => ({ data: { data: [] } })),
      ]);

      if (indicesRes.data?.indices) setIndices(indicesRes.data.indices);
      if (userRes.data?.user) setUser(userRes.data.user);
      if (portRes.data?.data) setPortfolio(portRes.data.data);
      if (transRes.data?.data) setTransactions(transRes.data.data);
    } catch (err) {
      console.error("Context fetch error:", err);
    }
  }, []);

  // Fetch specific ticker details (prices, sentiments, news)
  const fetchSymbolData = useCallback(async (sym) => {
    const cleanSym = (sym || "AAPL").toUpperCase().trim();
    setActiveSymbol(cleanSym);
    setLoading(true);
    setError("");

    try {
      const [sentRes, priceRes, newsRes] = await Promise.all([
        api.get(`/sentiment/${cleanSym}`),
        api.get(`/prices/${cleanSym}`),
        api.get(`/news/${cleanSym}`),
      ]);

      setSentiments(sentRes.data?.data || []);
      setPrices(priceRes.data?.data || []);
      setNews(newsRes.data?.data || []);
    } catch (err) {
      setSentiments([]);
      setPrices([]);
      setNews([]);
      setError(
        err.response?.status === 404
          ? `Symbol '${cleanSym}' not found in active market cache.`
          : "Temporary data feed connection error. Retrying..."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMarketContext();
    fetchSymbolData(activeSymbol);
    const interval = setInterval(fetchMarketContext, 30000);
    return () => clearInterval(interval);
  }, [fetchMarketContext]);

  // Current active asset stats
  const latestPrice = prices.length > 0 ? prices[prices.length - 1].close : null;
  const prevPrice = prices.length > 1 ? prices[prices.length - 2].close : latestPrice;
  const priceDelta = latestPrice && prevPrice ? latestPrice - prevPrice : 0;
  const priceDeltaPct = prevPrice ? (priceDelta / prevPrice) * 100 : 0;
  const isUp = priceDelta >= 0;

  return (
    <div className="space-y-4">
      {/* ── 1. Top Strip: Market Indices & Account Summary ── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-3">
        {/* Market Indices (8 Cols) */}
        <div className="xl:col-span-8 flex gap-2.5 overflow-x-auto no-scrollbar py-0.5">
          {indices.length > 0 ? (
            indices.map((idx) => {
              const up = (idx.change_pct || 0) >= 0;
              return (
                <div
                  key={idx.index_name}
                  className="terminal-card px-3.5 py-2.5 flex-shrink-0 min-w-[170px] flex flex-col justify-between font-mono"
                >
                  <div className="flex justify-between items-center text-[10px] text-slate-400">
                    <span className="font-bold text-slate-300">{idx.display_name || idx.index_name}</span>
                    <span className="text-[9px] text-slate-500">LIVE</span>
                  </div>
                  <div className="flex items-baseline justify-between mt-1">
                    <span className="text-sm font-bold text-white">
                      {Number(idx.current_value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}
                    </span>
                    <span className={`text-[11px] font-bold flex items-center gap-0.5 ${up ? "text-emerald-400" : "text-coral-400"}`}>
                      {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                      {up ? "+" : ""}{Number(idx.change_pct || 0).toFixed(2)}%
                    </span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="terminal-card px-4 py-2 flex items-center gap-2 text-xs font-mono text-slate-400">
              <Clock size={13} className="animate-spin text-cyan-400" />
              <span>SYNCING GLOBAL INDICES...</span>
            </div>
          )}
        </div>

        {/* Paper Account Summary Widget (4 Cols) */}
        <div className="xl:col-span-4 terminal-card p-2.5 flex items-center justify-between font-mono text-xs">
          <div className="flex items-center gap-2.5 pl-1">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Wallet size={16} />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">PORTFOLIO EQUITY</div>
              <div className="text-sm font-bold text-white">
                ${Number((user?.current_balance || 0) + (portfolio?.total_market_value || 0)).toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          <div className="text-right pr-1">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">UNREALIZED P&L</div>
            <div className={`text-xs font-bold ${portfolio.total_pnl >= 0 ? "text-emerald-400" : "text-coral-400"}`}>
              {portfolio.total_pnl >= 0 ? "+" : ""}${Number(portfolio.total_pnl || 0).toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* ── AI Market Intelligence Brief Strip ── */}
      <MarketBriefWidget />

      {/* ── 2. Symbol Command Header & Quick Switcher ── */}
      <div className="terminal-card p-3 flex flex-wrap items-center justify-between gap-3 font-mono">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-base font-bold text-white tracking-wider">{activeSymbol}</span>
            <span className="text-[10px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 px-1.5 py-0.5 rounded font-bold">
              TERMINAL ASSET
            </span>
          </div>

          {latestPrice != null && (
            <div className="flex items-baseline gap-2 pl-3 border-l border-white/10">
              <span className="text-lg font-bold text-white">${latestPrice.toFixed(2)}</span>
              <span className={`text-xs font-bold flex items-center gap-0.5 ${isUp ? "text-emerald-400" : "text-coral-400"}`}>
                {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                {isUp ? "+" : ""}{priceDelta.toFixed(2)} ({priceDeltaPct.toFixed(2)}%)
              </span>
            </div>
          )}
        </div>

        {/* Quick Ticker Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
          {DEFAULT_TICKERS.map((t) => (
            <button
              key={t.symbol}
              onClick={() => fetchSymbolData(t.symbol)}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                activeSymbol === t.symbol
                  ? "bg-white/10 text-white font-bold border border-white/15"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {t.symbol}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-3 rounded-lg bg-coral-500/10 border border-coral-500/20 text-xs font-mono text-coral-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
          <button
            onClick={() => fetchSymbolData(activeSymbol)}
            className="px-2 py-0.5 rounded bg-coral-500/20 hover:bg-coral-500/30 text-coral-300 font-bold"
          >
            RETRY
          </button>
        </div>
      )}

      {/* ── 3. Main Workspace Grid (Left: Charts & Table / Right: Execution & News) ── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Left Column (8 Cols) */}
        <div className="xl:col-span-8 space-y-4">
          {/* Stock Synthesis & Price Dynamics Card */}
          <StockIntelligenceCard symbol={activeSymbol} />

          {/* Main Price Chart */}
          <PriceChart prices={prices} sentiments={sentiments} ticker={activeSymbol} />

          {/* AI Sentiment Trend Oscillator */}
          <SentimentChart sentiments={sentiments} />

          {/* Active Holdings & Portfolio Table */}
          <div className="terminal-card p-4 font-mono">
            <div className="flex items-center justify-between mb-3 border-b border-white/5 pb-2">
              <span className="text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
                <Layers size={14} className="text-cyan-400" />
                ACTIVE HOLDINGS & POSITIONS ({portfolio.holdings?.length || 0})
              </span>
              <span className="text-[10px] text-slate-500">PAPER BROKERAGE LEDGER</span>
            </div>

            {portfolio.holdings && portfolio.holdings.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/5 text-[10px] text-slate-400 uppercase">
                      <th className="pb-2 font-semibold">TICKER</th>
                      <th className="pb-2 font-semibold text-right">SHARES</th>
                      <th className="pb-2 font-semibold text-right">AVG PRICE</th>
                      <th className="pb-2 font-semibold text-right">CURRENT VAL</th>
                      <th className="pb-2 font-semibold text-right">TOTAL INVESTED</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {portfolio.holdings.map((h) => (
                      <tr key={h.ticker} className="hover:bg-white/5 transition-colors">
                        <td className="py-2.5 font-bold text-white">{h.ticker}</td>
                        <td className="py-2.5 text-right text-slate-200">{Number(h.shares).toLocaleString()}</td>
                        <td className="py-2.5 text-right text-slate-300">${Number(h.avg_buy_price).toFixed(2)}</td>
                        <td className="py-2.5 text-right text-white font-bold">${Number(h.current_value || h.total_invested).toFixed(2)}</td>
                        <td className="py-2.5 text-right text-slate-400">${Number(h.total_invested).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-slate-500">
                NO ACTIVE PAPER HOLDINGS · EXECUTE A TRADE VIA THE DESK
              </div>
            )}
          </div>
        </div>

        {/* Right Column (4 Cols) */}
        <div className="xl:col-span-4 space-y-4">
          {/* Market Mood Barometer */}
          <MarketMood sentiments={sentiments} />

          {/* Quick Execution Terminal Panel */}
          <TradingPanel
            ticker={activeSymbol}
            sentimentScore={sentiments.length > 0 ? sentiments[0].sentiment_score : 0}
            sentimentLabel={sentiments.length > 0 ? sentiments[0].sentiment_label : "Neutral"}
            currentPrice={latestPrice || 0}
            balance={user?.current_balance || 0}
            onTradeSuccess={() => {
              fetchMarketContext();
            }}
          />

          {/* Real-time AI News Briefing Wire */}
          <NewsFeed news={news} />
        </div>
      </div>
    </div>
  );
}
