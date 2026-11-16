import React, { useState, useEffect } from "react";
import { Line, Pie } from "react-chartjs-2";
import api from "../utils/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { formatCurrency } from "../utils/currency";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Zap,
  AlertCircle,
  BarChart2,
  PieChart as PieIcon,
  Activity,
  ShieldAlert,
} from "lucide-react";
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
  Filler,
} from "chart.js";

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

function MetricTile({ title, value, subText, delta, isPositive, badge }) {
  return (
    <div className="terminal-card p-3.5 flex flex-col justify-between font-mono">
      <div className="flex items-center justify-between text-[10px] text-slate-400 font-semibold mb-1">
        <span>{title}</span>
        {badge && (
          <span className="text-[9px] bg-white/5 text-slate-400 px-1.5 py-0.5 rounded border border-white/5">
            {badge}
          </span>
        )}
      </div>

      <div className="flex items-baseline justify-between mt-1">
        <span className="text-lg font-bold text-white tracking-tight">{value}</span>
        {delta != null && (
          <span
            className={`text-xs font-bold flex items-center gap-0.5 ${
              isPositive ? "text-emerald-400" : "text-coral-400"
            }`}
          >
            {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {delta}
          </span>
        )}
      </div>

      {subText && <div className="text-[10px] text-slate-500 mt-1 truncate">{subText}</div>}
    </div>
  );
}

export default function AnalyticsDashboard() {
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
          api.get("/analytics/overview").catch(() => ({ data: {} })),
          api.get(`/analytics/history?days=${timeRange}`).catch(() => ({ data: {} })),
          api.get("/analytics/sectors").catch(() => ({ data: {} })),
          api.get("/analytics/risk").catch(() => ({ data: {} })),
          api.get("/analytics/top-performers").catch(() => ({ data: {} })),
        ]);

      setAnalytics(analyticsRes.data || {});
      setHistory(historyRes.data || {});
      setSectors(sectorsRes.data || {});
      setRisk(riskRes.data || {});
      setPerformers(performersRes.data || {});
    } catch (error) {
      console.error("Analytics fetch error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllAnalytics();
  }, [timeRange]);

  const performanceChartData = {
    labels: history?.dates || [],
    datasets: [
      {
        label: "Portfolio Value",
        data: history?.values || [],
        borderColor: "#10b981",
        backgroundColor: "rgba(16, 185, 129, 0.08)",
        borderWidth: 2,
        tension: 0.2,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
      {
        label: "S&P 500 Benchmark",
        data: history?.benchmark_values || [],
        borderColor: "#38bdf8",
        backgroundColor: "transparent",
        borderDash: [4, 4],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.2,
      },
    ],
  };

  const sectorChartData = {
    labels: sectors?.sectors || [],
    datasets: [
      {
        data: sectors?.percentages || [],
        backgroundColor: [
          "#10b981",
          "#06b6d4",
          "#3b82f6",
          "#f59e0b",
          "#8b5cf6",
          "#ec4899",
          "#f43f5e",
          "#64748b",
        ],
        borderColor: "#070b12",
        borderWidth: 2,
      },
    ],
  };

  return (
    <div className="space-y-4 font-mono">
      {/* ── 1. Top KPI Rows: Portfolio Equity, Cash, and P&L Segregation ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricTile
          title="PORTFOLIO EQUITY"
          value={
            analytics?.portfolio_equity != null
              ? formatCurrency(analytics.portfolio_equity, currency)
              : formatCurrency(
                  (analytics?.cash_balance || 0) + (analytics?.known_market_value || 0),
                  currency
                )
          }
          subText={`Holdings: ${
            analytics?.total_value != null
              ? formatCurrency(analytics.total_value, currency)
              : analytics?.known_market_value != null
              ? `${formatCurrency(analytics.known_market_value, currency)} (Partial)`
              : "Unavailable"
          }`}
          badge="NET ASSETS"
        />

        <MetricTile
          title="CASH & BUYING POWER"
          value={formatCurrency(analytics?.buying_power || 0, currency)}
          subText={`Cash: ${formatCurrency(analytics?.cash_balance || 0, currency)} | Rsv: ${formatCurrency(
            analytics?.reserved_cash || 0,
            currency
          )}`}
          badge="LIQUIDITY"
        />

        <MetricTile
          title="UNREALIZED P&L"
          value={
            analytics?.unrealized_pnl != null
              ? `${analytics.unrealized_pnl >= 0 ? "+" : ""}${formatCurrency(
                  analytics.unrealized_pnl,
                  currency
                )}`
              : "Unavailable"
          }
          delta={
            analytics?.unrealized_return_pct != null
              ? `${analytics.unrealized_return_pct >= 0 ? "+" : ""}${analytics.unrealized_return_pct}%`
              : null
          }
          isPositive={(analytics?.unrealized_pnl || 0) >= 0}
          subText={`Active Cost: ${formatCurrency(analytics?.total_invested || 0, currency)}`}
          badge="OPEN"
        />

        <MetricTile
          title="REALIZED P&L"
          value={`${(analytics?.realized_pnl || 0) >= 0 ? "+" : ""}${formatCurrency(
            analytics?.realized_pnl || 0,
            currency
          )}`}
          delta={
            analytics?.realized_return_pct != null
              ? `${analytics.realized_return_pct >= 0 ? "+" : ""}${analytics.realized_return_pct}%`
              : null
          }
          isPositive={(analytics?.realized_pnl || 0) >= 0}
          subText={`Closed Cost: ${formatCurrency(
            analytics?.closed_cost_basis || 0,
            currency
          )}`}
          badge="CLOSED"
        />
      </div>

      {/* ── 1b. Secondary KPI Row: Win Rate & Bot vs Manual Attribution ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricTile
          title="TOTAL COMBINED P&L"
          value={
            analytics?.total_pnl != null
              ? `${analytics.total_pnl >= 0 ? "+" : ""}${formatCurrency(
                  analytics.total_pnl,
                  currency
                )}`
              : "Unavailable"
          }
          delta={
            analytics?.total_pnl_pct != null
              ? `${analytics.total_pnl_pct >= 0 ? "+" : ""}${analytics.total_pnl_pct}%`
              : null
          }
          isPositive={(analytics?.total_pnl || 0) >= 0}
          subText={`Deposit: ${formatCurrency(analytics?.starting_balance || 0, currency)}`}
          badge="COMBINED"
        />

        <MetricTile
          title="WIN RATE (CLOSED)"
          value={
            analytics?.win_rate_raw != null
              ? `${analytics.win_rate_raw}%`
              : "N/A"
          }
          subText={`${analytics?.winning_trades || 0} Wins / ${analytics?.losing_trades || 0} Losses / ${
            analytics?.breakeven_trades || 0
          } Even`}
          isPositive={(analytics?.win_rate || 0) >= 50}
          badge="ACCURACY"
        />

        <MetricTile
          title="BOT PERFORMANCE"
          value={`${(analytics?.bot_performance?.total_pnl || 0) >= 0 ? "+" : ""}${formatCurrency(
            analytics?.bot_performance?.total_pnl || 0,
            currency
          )}`}
          subText={`${analytics?.bot_performance?.total_trades || 0} Trades | Win: ${
            analytics?.bot_performance?.win_rate != null
              ? `${analytics.bot_performance.win_rate}%`
              : "N/A"
          }`}
          isPositive={(analytics?.bot_performance?.total_pnl || 0) >= 0}
          badge="BOT"
        />

        <MetricTile
          title="MANUAL PERFORMANCE"
          value={`${(analytics?.manual_performance?.total_pnl || 0) >= 0 ? "+" : ""}${formatCurrency(
            analytics?.manual_performance?.total_pnl || 0,
            currency
          )}`}
          subText={`${analytics?.manual_performance?.total_trades || 0} Trades | Win: ${
            analytics?.manual_performance?.win_rate != null
              ? `${analytics.manual_performance.win_rate}%`
              : "N/A"
          }`}
          isPositive={(analytics?.manual_performance?.total_pnl || 0) >= 0}
          badge="MANUAL"
        />
      </div>

      {/* ── 2. Performance Benchmark Chart ── */}
      <div className="terminal-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3 border-b border-white/5 pb-2">
          <div>
            <span className="text-xs font-bold text-white tracking-wider">
              EQUITY CURVE VS BENCHMARK
            </span>
            <span className="text-[10px] text-slate-500 ml-2">SIMULATION HISTORY</span>
          </div>

          <div className="flex items-center gap-1 text-[10px]">
            {[
              { label: "1W", days: 7 },
              { label: "1M", days: 30 },
              { label: "3M", days: 90 },
              { label: "1Y", days: 365 },
            ].map((t) => (
              <button
                key={t.days}
                onClick={() => setTimeRange(t.days)}
                className={`px-2 py-0.5 rounded transition-colors ${
                  timeRange === t.days
                    ? "bg-white/10 text-white font-bold border border-white/10"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="h-72 w-full">
          {history?.dates?.length > 0 ? (
            <Line
              data={performanceChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    display: true,
                    position: "top",
                    align: "end",
                    labels: {
                      boxWidth: 8,
                      usePointStyle: true,
                      color: "#94a3b8",
                      font: { family: "monospace", size: 10 },
                    },
                  },
                  tooltip: {
                    backgroundColor: "#070b12",
                    borderColor: "rgba(255,255,255,0.14)",
                    borderWidth: 1,
                    titleFont: { family: "monospace", size: 10 },
                    bodyFont: { family: "monospace", size: 11 },
                    displayColors: false,
                  },
                },
                scales: {
                  y: {
                    position: "right",
                    grid: { color: "rgba(255,255,255,0.04)" },
                    ticks: { color: "#64748b", font: { family: "monospace", size: 10 } },
                  },
                  x: {
                    grid: { display: false },
                    ticks: {
                      color: "#64748b",
                      font: { family: "monospace", size: 10 },
                      maxTicksLimit: 8,
                    },
                  },
                },
              }}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500">
              ACCUMULATING HISTORICAL EQUITY DATA POINTS
            </div>
          )}
        </div>
      </div>

      {/* ── 3. Sector Exposure & Risk Profile Matrix ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Sector Allocation Donut (5 Cols) */}
        <div className="lg:col-span-5 terminal-card p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
            <span className="text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
              <PieIcon size={14} className="text-cyan-400" />
              SECTOR ALLOCATION
            </span>
            <span className="text-[10px] text-slate-500">EXPOSURE WEIGHT</span>
          </div>

          <div className="h-56 flex items-center justify-center">
            {sectors?.sectors?.length > 0 ? (
              <Pie
                data={sectorChartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      position: "right",
                      labels: {
                        boxWidth: 8,
                        usePointStyle: true,
                        color: "#94a3b8",
                        font: { family: "monospace", size: 9 },
                      },
                    },
                  },
                }}
              />
            ) : (
              <div className="text-xs text-slate-500">NO ACTIVE EQUITY POSITIONS ALLOCATED</div>
            )}
          </div>
        </div>

        {/* Risk Metrics & Performers Table (7 Cols) */}
        <div className="lg:col-span-7 terminal-card p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
            <span className="text-xs font-bold text-white tracking-wider flex items-center gap-1.5">
              <ShieldAlert size={14} className="text-coral-400" />
              PORTFOLIO RISK METRICS & ATTRIBUTION
            </span>
            <span className="text-[10px] text-slate-500">PARAMETRIC MODEL</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            <div className="p-2.5 rounded bg-black/40 border border-white/5">
              <div className="text-[9px] text-slate-400 font-bold">BETA (VS SPY)</div>
              <div className="text-sm font-bold text-white mt-0.5">
                {risk?.beta != null ? Number(risk.beta).toFixed(2) : "N/A"}
              </div>
            </div>
            <div className="p-2.5 rounded bg-black/40 border border-white/5">
              <div className="text-[9px] text-slate-400 font-bold">MAX DRAWDOWN</div>
              <div className="text-sm font-bold text-coral-400 mt-0.5">
                {risk?.max_drawdown != null
                  ? `-${Number(risk.max_drawdown).toFixed(1)}%`
                  : analytics?.max_drawdown != null
                  ? `-${Number(analytics.max_drawdown).toFixed(1)}%`
                  : "N/A"}
              </div>
            </div>
            <div className="p-2.5 rounded bg-black/40 border border-white/5">
              <div className="text-[9px] text-slate-400 font-bold">SHARPE RATIO</div>
              <div className="text-sm font-bold text-slate-200 mt-0.5">
                {analytics?.sharpe_ratio != null ? Number(analytics.sharpe_ratio).toFixed(2) : "N/A"}
              </div>
            </div>
            <div className="p-2.5 rounded bg-black/40 border border-white/5">
              <div className="text-[9px] text-slate-400 font-bold">PROFIT FACTOR</div>
              <div className="text-sm font-bold text-emerald-400 mt-0.5">
                {analytics?.profit_factor === Infinity
                  ? "∞"
                  : analytics?.profit_factor != null
                  ? Number(analytics.profit_factor).toFixed(2)
                  : "N/A"}
              </div>
            </div>
          </div>

          {/* Top Asset Performers */}
          <div className="border-t border-white/5 pt-2">
            <div className="text-[10px] text-slate-400 font-bold uppercase mb-1.5">
              TOP ATTRIBUTION CONTRIBUTORS
            </div>
            <div className="space-y-1">
              {(performers?.top_performers || performers?.top || []).length > 0 ? (
                (performers?.top_performers || performers?.top).map((item) => {
                  const sym = item.symbol || item.ticker;
                  const isUp = (item.pnl || 0) >= 0;
                  return (
                    <div
                      key={sym}
                      className="flex items-center justify-between text-xs p-1.5 rounded hover:bg-white/5"
                    >
                      <span className="font-bold text-white">{sym}</span>
                      <div className="flex gap-4">
                        <span
                          className={`font-bold ${
                            isUp ? "text-emerald-400" : "text-coral-400"
                          }`}
                        >
                          {isUp ? "+" : ""}${Number(item.pnl || 0).toFixed(2)}
                        </span>
                        <span
                          className={`font-bold ${
                            isUp ? "text-emerald-400" : "text-coral-400"
                          }`}
                        >
                          {isUp ? "+" : ""}{Number(item.pnl_pct || item.return_pct || 0).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-slate-500 py-2">
                  NO ASSET ATTRIBUTION CONTRIBUTORS RECORDED
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
