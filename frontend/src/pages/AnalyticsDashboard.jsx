import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Line, Pie } from 'react-chartjs-2';
import api from '../utils/api';
import { useCurrency } from '../contexts/CurrencyContext';
import { formatCurrency } from '../utils/currency';
import { TrendingUp, TrendingDown, Target, Zap, AlertCircle, BarChart2, PieChart as PieIcon, Activity } from 'lucide-react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    Filler
} from 'chart.js';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

const AnalyticsDashboard = () => {
    const { currency } = useCurrency();
    const [analytics, setAnalytics] = useState(null);
    const [history, setHistory] = useState(null);
    const [sectors, setSectors] = useState(null);
    const [risk, setRisk] = useState(null);
    const [performers, setPerformers] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState(30);

    const fetchAllAnalytics = async () => {
        try {
            setLoading(true);
            const [analyticsRes, historyRes, sectorsRes, riskRes, performersRes] =
                await Promise.all([
                    api.get('/analytics/overview'),
                    api.get(`/analytics/history?days=${timeRange}`),
                    api.get('/analytics/sectors'),
                    api.get('/analytics/risk'),
                    api.get('/analytics/top-performers')
                ]);

            setAnalytics(analyticsRes.data);
            setHistory(historyRes.data);
            setSectors(sectorsRes.data);
            setRisk(riskRes.data);
            setPerformers(performersRes.data);
        } catch (error) {
            console.error('Error fetching analytics:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAllAnalytics();
    }, [timeRange]);

    if (loading && !analytics) {
        return (
            <div className="py-20 flex flex-col items-center">
                <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-4 text-slate-400 font-medium animate-pulse">Analyzing your portfolio performance...</p>
            </div>
        );
    }

    const performanceChartData = {
        labels: history?.dates || [],
        datasets: [
            {
                label: 'Portfolio Value',
                data: history?.values || [],
                borderColor: '#00ff88',
                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 2,
            },
            {
                label: 'S&P 500 Benchmark',
                data: history?.benchmark_values || [],
                borderColor: '#3b82f6',
                backgroundColor: 'transparent',
                borderDash: [5, 5],
                pointRadius: 0,
                tension: 0.4,
            }
        ]
    };

    const sectorChartData = {
        labels: sectors?.sectors || [],
        datasets: [{
            data: sectors?.percentages || [],
            backgroundColor: [
                '#10b981', '#3b82f6', '#f59e0b', '#ef4444',
                '#8b5cf6', '#ec4899', '#06b6d4', '#475569'
            ],
            borderWidth: 0,
        }]
    };

    return (
        <div className="space-y-8 pb-12">
            {/* Stat Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Total Net Value"
                    value={formatCurrency(analytics?.total_value, currency)}
                    subText={`Invested: ${formatCurrency(analytics?.total_invested, currency)}`}
                    icon={<BarChart2 className="w-5 h-5 text-blue-500" />}
                />
                <StatCard
                    title="Total P&L"
                    value={formatCurrency(analytics?.total_pnl, currency)}
                    percentage={`${analytics?.total_pnl_pct}%`}
                    isPositive={analytics?.total_pnl >= 0}
                    icon={<Zap className="w-5 h-5 text-yellow-500" />}
                />
                <StatCard
                    title="Win Rate"
                    value={`${analytics?.win_rate}%`}
                    subText={`${analytics?.winning_trades} Win / ${analytics?.losing_trades} Loss`}
                    icon={<Target className="w-5 h-5 text-green-500" />}
                />
                <StatCard
                    title="Sharpe Ratio"
                    value={analytics?.sharpe_ratio}
                    subText={`Vol: ${analytics?.volatility}%`}
                    icon={<Activity className="w-5 h-5 text-purple-500" />}
                />
            </div>

            {/* Main performance chart */}
            <div className="card p-6">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white">Portfolio Performance</h3>
                    <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                        {[7, 30, 90, 365].map(days => (
                            <button
                                key={days}
                                onClick={() => setTimeRange(days)}
                                className={`px-3 py-1 rounded text-xs font-bold transition-all ${timeRange === days ? 'bg-white dark:bg-slate-700 shadow-sm text-accent' : 'text-slate-500'}`}
                            >
                                {days === 365 ? '1Y' : `${days / 7 >= 1 ? days / 7 + 'W' : days + 'D'}`}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="h-80">
                    <Line
                        data={performanceChartData}
                        options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                                x: { grid: { display: false }, ticks: { display: false } }
                            }
                        }}
                    />
                </div>
            </div>

            {/* Grid for Sector and Risk */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <PieIcon className="w-5 h-5 text-accent" />
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">Sector Allocation</h3>
                    </div>
                    <div className="flex flex-col md:flex-row items-center gap-8">
                        <div className="w-48 h-48">
                            <Pie data={sectorChartData} options={{ plugins: { legend: { display: false } } }} />
                        </div>
                        <div className="flex-1 space-y-3">
                            {sectors?.sectors.map((s, i) => (
                                <div key={i} className="flex justify-between items-center text-sm">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: sectorChartData.datasets[0].backgroundColor[i] }}></div>
                                        <span className="text-slate-600 dark:text-slate-400">{s}</span>
                                    </div>
                                    <span className="font-bold text-slate-900 dark:text-white">{sectors.percentages[i]}%</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <AlertCircle className="w-5 h-5 text-orange-500" />
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">Risk Metrics</h3>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <RiskMetric label="Beta (Market Relation)" value={risk?.beta} detail="1.0 = Moves with Market" />
                        <RiskMetric label="Alpha (Excess Return)" value={`${risk?.alpha}%`} detail="Annualized Performance" />
                        <RiskMetric label="R-Squared" value={risk?.r_squared} detail="Correlation Strength" />
                        <RiskMetric label="Sortino Ratio" value={risk?.sortino_ratio} detail="Downside Risk Adjusted" />
                        <RiskMetric label="Max Drawdown" value={`${analytics?.max_drawdown}%`} detail="Peak to Bottom" />
                    </div>
                </div>
            </div>

            {/* Performers Table */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                <div className="card overflow-hidden">
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800">
                        <h3 className="text-lg font-bold flex items-center gap-2 text-green-500">
                            <TrendingUp className="w-5 h-5" /> Top Performers
                        </h3>
                    </div>
                    <PerformerTable data={performers?.top_performers} />
                </div>
                <div className="card overflow-hidden">
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800">
                        <h3 className="text-lg font-bold flex items-center gap-2 text-rose-500">
                            <TrendingDown className="w-5 h-5" /> Worst Performers
                        </h3>
                    </div>
                    <PerformerTable data={performers?.worst_performers} />
                </div>
            </div>

        </div>
    );
};

const StatCard = ({ title, value, percentage, subText, icon, isPositive }) => (
    <div className="card p-6 relative overflow-hidden group">
        <div className="absolute top-0 right-0 p-3 opacity-20 transition-transform group-hover:scale-110">
            {icon}
        </div>
        <p className="text-sm font-bold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-tight">{title}</p>
        <div className="flex items-baseline gap-3">
            <h2 className="text-2xl font-black text-slate-900 dark:text-white">{value}</h2>
            {percentage && (
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${isPositive ? 'bg-green-500/10 text-green-500' : 'bg-rose-500/10 text-rose-500'}`}>
                    {isPositive ? '+' : ''}{percentage}
                </span>
            )}
        </div>
        {subText && <p className="text-xs text-slate-500 mt-2 font-medium">{subText}</p>}
    </div>
);

const RiskMetric = ({ label, value, detail }) => (
    <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
        <p className="text-xs font-bold text-slate-500 uppercase mb-1">{label}</p>
        <h4 className="text-lg font-black text-slate-900 dark:text-white">{value}</h4>
        <p className="text-[10px] text-slate-400 mt-1 uppercase font-bold">{detail}</p>
    </div>
);

const PerformerTable = ({ data }) => (
    <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-500 uppercase bg-slate-50 dark:bg-slate-800/30">
                <tr>
                    <th className="px-6 py-4 font-black">Ticker</th>
                    <th className="px-6 py-4 font-black">Holdings</th>
                    <th className="px-6 py-4 font-black text-right">P&L (%)</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data?.map((p, i) => (
                    <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors">
                        <td className="px-6 py-4 font-bold text-slate-900 dark:text-white">{p.ticker}</td>
                        <td className="px-6 py-4 text-slate-500">{p.shares} shares</td>
                        <td className={`px-6 py-4 text-right font-black ${p.pnl >= 0 ? 'text-green-500' : 'text-rose-500'}`}>
                            {p.pnl >= 0 ? '+' : ''}{p.pnl_pct}%
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
);

export default AnalyticsDashboard;
