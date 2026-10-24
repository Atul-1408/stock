import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, TrendingDown, Globe2, Activity, Briefcase } from "lucide-react";
import { useCurrency, getNativeCurrency } from "../contexts/CurrencyContext";
import { formatCurrency } from "../utils/currency";
import { tickerService } from "../services/TickerService";
import api from "../utils/api";

import SearchBar from "../components/SearchBar";
import SentimentChart from "../components/SentimentChart";
import PriceChart from "../components/PriceChart";
import NewsFeed from "../components/NewsFeed";
import MarketMood from "../components/MarketMood";
import StockSidebar from "../components/StockSidebar";
import TradingPanel from "../components/TradingPanel";
import Portfolio from "../components/Portfolio";
import TransactionHistory from "../components/TransactionHistory";

const getMoodData = (sentiments) => {
    if (!sentiments || sentiments.length === 0) return { score: 0, label: 'Neutral' };
    const avg = sentiments.reduce((acc, s) => acc + s.sentiment_score, 0) / sentiments.length;
    if (avg > 0.1) return { score: avg, label: 'Positive' };
    if (avg < -0.1) return { score: avg, label: 'Negative' };
    return { score: avg, label: 'Neutral' };
};

// Quick-look market cards shown before any stock is searched
const QUICK_TICKERS = [
    { t: "RELIANCE.NS", n: "Reliance Ind.", flag: "🇮🇳" },
    { t: "TCS.NS", n: "TCS", flag: "🇮🇳" },
    { t: "HDFCBANK.NS", n: "HDFC Bank", flag: "🇮🇳" },
    { t: "AAPL", n: "Apple", flag: "🇺🇸" },
    { t: "TSLA", n: "Tesla", flag: "🇺🇸" },
    { t: "NVDA", n: "NVIDIA", flag: "🇺🇸" },
];

function MarketOverview({ onSelect }) {
    const { currency, convertPrice } = useCurrency();
    const [cards, setCards] = useState(QUICK_TICKERS.map(t => ({ ...t, price: null, change: null, changePct: null })));

    useEffect(() => {
        const componentId = 'dashboard-overview';
        
        const handleUpdate = (data) => {
            const map = {};
            data.forEach(row => { map[row.ticker] = row; });
            setCards(QUICK_TICKERS.map(q => ({
                ...q,
                ...(map[q.t] || {}),
            })));
        };

        const dashboardTickers = QUICK_TICKERS.map(t => t.t);

        // Subscribe for updates
        tickerService.subscribe(componentId, handleUpdate, dashboardTickers);

        return () => {
            tickerService.unsubscribe(componentId);
        };
    }, []);

    return (
        <motion.div
            key="overview"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-6"
        >
            <div className="flex items-center gap-2 mb-2">
                <Globe2 className="w-4 h-4 text-accent" />
                <span className="text-xs font-black tracking-widest uppercase text-slate-500">Market Snapshot</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {cards.map((c) => {
                    const up = c.change === null ? null : c.change >= 0;
                    return (
                        <motion.button
                            key={c.t}
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => onSelect(c.t)}
                            className="card p-5 text-left group hover:border-accent/40 transition-all"
                        >
                            <div className="flex justify-between items-start mb-3">
                                <span className="text-lg">{c.flag}</span>
                                {up !== null && (
                                    <span className={`flex items-center gap-0.5 text-xs font-bold px-2 py-0.5 rounded-full ${up ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                                        {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                        {up && "+"}{c.changePct?.toFixed(2)}%
                                    </span>
                                )}
                            </div>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{c.n}</p>
                            <p className="text-xl font-black text-slate-900 dark:text-white">
                                {c.price ? formatCurrency(convertPrice(c.price, getNativeCurrency(c.t)), currency) : "—"}
                            </p>
                            <p className={`text-xs mt-1 font-semibold ${up ? 'text-emerald-400' : up === null ? 'text-slate-500' : 'text-rose-400'}`}>
                                {c.change !== null ? `${c.change >= 0 ? "+" : ""}${c.change?.toFixed(2)}` : "Loading…"}
                            </p>
                            <div className="mt-3 text-[10px] font-bold text-accent opacity-0 group-hover:opacity-100 transition-opacity uppercase tracking-widest">
                                Analyze →
                            </div>
                        </motion.button>
                    );
                })}
            </div>
            <div className="card p-6 border-dashed border-2 bg-slate-500/5 dark:bg-slate-400/5">
                <div className="flex items-center gap-3 mb-3">
                    <Activity className="w-5 h-5 text-accent" />
                    <p className="font-black text-slate-700 dark:text-slate-200">Select a stock to begin analysis</p>
                </div>
                <p className="text-sm text-slate-500">
                    Click any card above or use the sidebar to explore sentiment, price charts, and AI-powered news briefings.
                </p>
            </div>
        </motion.div>
    );
}

const Dashboard = () => {
    const [ticker, setTicker] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [hasSearched, setHasSearched] = useState(false);

    const [sentiments, setSentiments] = useState([]);
    const [prices, setPrices] = useState([]);
    const [news, setNews] = useState([]);

    const [balance, setBalance] = useState(0);
    const [portfolioData, setPortfolioData] = useState({ holdings: [], total_market_value: 0, total_pnl: 0 });
    const [transactions, setTransactions] = useState([]);
    const [userLoading, setUserLoading] = useState(true);

    const refreshUserData = async () => {
        try {
            const [userRes, portfolioRes, transRes] = await Promise.all([
                api.get('/auth/me'),
                api.get('/portfolio'),
                api.get('/transactions?limit=10')
            ]);
            setBalance(userRes.data.user.current_balance);
            setPortfolioData(portfolioRes.data.data);
            setTransactions(transRes.data.data);
        } catch (err) {
            console.error("Error fetching user data", err);
        } finally {
            setUserLoading(false);
        }
    };

    useEffect(() => { refreshUserData(); }, []);

    const fetchDashboardData = async (nextTicker) => {
        const cleanTicker = (nextTicker || "").toUpperCase().trim();
        if (!cleanTicker) return;

        setHasSearched(true);
        setTicker(cleanTicker);
        setError("");
        setLoading(true);

        try {
            const cached = sessionStorage.getItem(`cache_${cleanTicker}`);
            if (cached) {
                const { sentiments, prices, news } = JSON.parse(cached);
                setSentiments(sentiments);
                setPrices(prices);
                setNews(news);
                setLoading(false);
                return;
            }

            const [sentimentRes, pricesRes, newsRes] = await Promise.all([
                api.get(`/sentiment/${cleanTicker}`),
                api.get(`/prices/${cleanTicker}`),
                api.get(`/news/${cleanTicker}`),
            ]);

            const data = {
                sentiments: sentimentRes.data?.data || [],
                prices: pricesRes.data?.data || [],
                news: newsRes.data?.data || [],
            };

            setSentiments(data.sentiments);
            setPrices(data.prices);
            setNews(data.news);

            sessionStorage.setItem(`cache_${cleanTicker}`, JSON.stringify(data));
        } catch (err) {
            setSentiments([]);
            setPrices([]);
            setNews([]);

            if (!err.response) {
                setError("Network error: Cannot connect to backend. Please ensure Flask API is running.");
            } else if (err.response.status === 429) {
                setError("Too many requests. Please wait a moment and try again.");
            } else if (err.response.status === 404) {
                setError(`Ticker '${cleanTicker}' not found. Please verify the symbol (e.g., AAPL).`);
            } else {
                setError("An unexpected error occurred while fetching dashboard data.");
            }
        } finally {
            setLoading(false);
        }
    };

    // Show data if we have ANY of prices/news/sentiments
    const hasData = prices.length > 0 || news.length > 0 || sentiments.length > 0;

    return (
        <div className="flex flex-col lg:flex-row gap-6">
            {/* Left Sidebar */}
            <div className="hidden lg:block w-64 xl:w-72 flex-shrink-0">
                <StockSidebar activeTicker={ticker} onSelect={fetchDashboardData} />
            </div>

            <div className="flex-1 w-full min-w-0">
                <SearchBar onSearch={fetchDashboardData} loading={loading} />

                <div className="mt-6">
                    <AnimatePresence mode="wait">
                        {!hasSearched ? (
                            <MarketOverview key="overview" onSelect={fetchDashboardData} />
                        ) : error ? (
                            <motion.div
                                key="error"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="rounded-2xl border border-rose-400/30 bg-rose-500/10 p-8 text-center"
                            >
                                <div className="text-rose-500 text-3xl mb-4">⚠️</div>
                                <p className="text-lg font-medium mb-4 text-slate-800 dark:text-slate-200">{error}</p>
                                <button
                                    onClick={() => fetchDashboardData(ticker)}
                                    className="px-6 py-2 bg-rose-500 text-white rounded-lg hover:bg-rose-600 transition-colors shadow-lg shadow-rose-900/20"
                                >
                                    Try Again
                                </button>
                            </motion.div>
                        ) : hasData && !loading ? (
                            <motion.main
                                key="data"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="space-y-6"
                            >
                                {sentiments.length > 0 && <MarketMood sentiments={sentiments} />}

                                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                                    {/* Left Column: Charts and News */}
                                    <div className="xl:col-span-2 space-y-6">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                            <SentimentChart sentiments={sentiments} />
                                            <PriceChart prices={prices} sentiments={sentiments} />
                                        </div>
                                        <NewsFeed news={news} />
                                    </div>

                                    {/* Right Column: Trading and Portfolio */}
                                    <div className="xl:col-span-1 space-y-6">
                                        <TradingPanel
                                            ticker={ticker}
                                            currentPrice={prices.length > 0 ? prices[prices.length - 1].close : 0}
                                            balance={balance}
                                            sentimentScore={getMoodData(sentiments).score}
                                            sentimentLabel={getMoodData(sentiments).label}
                                            onTradeSuccess={(tradeResult) => {
                                                setBalance(tradeResult.balance);
                                                setPortfolioData(tradeResult.portfolio);
                                                // Also refresh transactions to show the new one
                                                api.get('/transactions?limit=10').then(res => setTransactions(res.data.data));
                                            }}
                                        />

                                        <section>
                                            <div className="flex items-center gap-3 mb-6">
                                                <div className="p-2 bg-blue-500/10 rounded-lg">
                                                    <Briefcase className="w-5 h-5 text-blue-500" />
                                                </div>
                                                <h3 className="text-xl font-black text-slate-900 dark:text-white">Your Portfolio</h3>
                                            </div>
                                            <Portfolio data={portfolioData} loading={userLoading} />
                                        </section>

                                        <TransactionHistory data={transactions} loading={userLoading} />
                                    </div>
                                </div>
                            </motion.main>
                        ) : null}

                        {loading && (
                            <motion.div
                                key="loading"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="py-20 flex flex-col items-center"
                            >
                                <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
                                <p className="mt-4 text-slate-600 dark:text-slate-400 font-medium animate-pulse">
                                    Gathering market insights for {ticker}...
                                </p>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
