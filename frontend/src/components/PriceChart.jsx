import React, { useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { Activity, ShieldAlert } from "lucide-react";
import { sentimentLabelToSignedScore } from "../utils/sentiment";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export default function PriceChart({ prices, sentiments, ticker }) {
  const [activeRange, setActiveRange] = useState("ALL");

  if (!prices || prices.length === 0) {
    return (
      <div className="terminal-card p-8 h-[340px] flex flex-col items-center justify-center border-dashed">
        <Activity className="w-8 h-8 text-slate-500 mb-2 opacity-50" />
        <p className="font-mono text-xs text-slate-400 font-semibold">NO HISTORICAL PRICE FEED AVAILABLE</p>
        <p className="text-[11px] text-slate-500 mt-1">Select an active ticker symbol from the desk</p>
      </div>
    );
  }

  const sortedPrices = [...prices].sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));

  // Range filtering
  let filteredPrices = sortedPrices;
  if (activeRange === "1W" && sortedPrices.length > 5) {
    filteredPrices = sortedPrices.slice(-5);
  } else if (activeRange === "1M" && sortedPrices.length > 22) {
    filteredPrices = sortedPrices.slice(-22);
  }

  const sentimentByDay = (sentiments || []).reduce((acc, row) => {
    const key = (row.analyzed_at || row.published_at || "").slice(0, 10);
    if (!key) return acc;
    const signed = sentimentLabelToSignedScore(row.sentiment_label, row.sentiment_score);
    if (!acc[key]) acc[key] = [];
    acc[key].push(signed);
    return acc;
  }, {});

  const labels = filteredPrices.map((row) => row.trade_date);
  const closeData = filteredPrices.map((row) => row.close);

  const isUp = closeData.length > 1 ? closeData[closeData.length - 1] >= closeData[0] : true;
  const strokeColor = isUp ? "#10b981" : "#f43f5e";
  const fillColor = isUp ? "rgba(16, 185, 129, 0.08)" : "rgba(244, 63, 94, 0.08)";

  const data = {
    labels,
    datasets: [
      {
        label: "Close Price",
        data: closeData,
        yAxisID: "y",
        borderColor: strokeColor,
        backgroundColor: fillColor,
        borderWidth: 1.75,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: strokeColor,
        fill: true,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#070b12",
        borderColor: "rgba(255, 255, 255, 0.14)",
        borderWidth: 1,
        titleColor: "#94a3b8",
        bodyColor: "#f8fafc",
        titleFont: { family: "monospace", size: 10 },
        bodyFont: { family: "monospace", size: 12, weight: "bold" },
        padding: 8,
        displayColors: false,
        callbacks: {
          label: (ctx) => ` Price: $${Number(ctx.raw).toFixed(2)}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          color: "#64748b",
          font: { family: "monospace", size: 10 },
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 6,
        },
      },
      y: {
        position: "right",
        grid: { color: "rgba(255, 255, 255, 0.04)" },
        ticks: {
          color: "#64748b",
          font: { family: "monospace", size: 10 },
          callback: (val) => `$${Number(val).toFixed(2)}`,
        },
      },
    },
  };

  return (
    <div className="terminal-card p-4 flex flex-col h-[360px]">
      {/* Chart Sub-header with range controls */}
      <div className="flex items-center justify-between mb-3 border-b border-white/5 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-white tracking-wider">
            {ticker || "ASSET"} // PRICE TRAJECTORY
          </span>
          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
            EOD FEED
          </span>
        </div>

        <div className="flex items-center gap-1 font-mono text-[10px]">
          {["1W", "1M", "ALL"].map((range) => (
            <button
              key={range}
              onClick={() => setActiveRange(range)}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeRange === range
                  ? "bg-white/10 text-white font-bold border border-white/10"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="flex-1 w-full min-h-0">
        <Line data={data} options={options} />
      </div>

      {/* Compliance Disclaimer */}
      <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[10px] font-mono text-slate-500">
        <span>DATA SOURCE: MARKET FEED CACHE</span>
        <span>PAPER SIMULATION · NOT FINANCIAL ADVICE</span>
      </div>
    </div>
  );
}
