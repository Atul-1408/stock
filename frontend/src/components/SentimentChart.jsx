import React from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { sentimentLabelToSignedScore } from "../utils/sentiment";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

export default function SentimentChart({ sentiments }) {
  if (!sentiments || sentiments.length === 0) {
    return (
      <div className="terminal-card p-6 h-[220px] flex flex-col items-center justify-center border-dashed">
        <p className="font-mono text-xs text-slate-500 font-semibold">NO SENTIMENT VECTORS RECORDED</p>
      </div>
    );
  }

  const sorted = [...sentiments].sort(
    (a, b) => new Date(a.analyzed_at || a.published_at) - new Date(b.analyzed_at || b.published_at)
  );

  const labels = sorted.map((row) => (row.analyzed_at || row.published_at || "").slice(0, 10));
  const signedScores = sorted.map((row) =>
    sentimentLabelToSignedScore(row.sentiment_label, row.sentiment_score)
  );

  const trendUp =
    signedScores.length > 1
      ? signedScores[signedScores.length - 1] - signedScores[0] >= 0
      : true;

  const color = trendUp ? "#10b981" : "#f43f5e";
  const gradientColor = trendUp ? "rgba(16, 185, 129, 0.08)" : "rgba(244, 63, 94, 0.08)";

  const data = {
    labels,
    datasets: [
      {
        label: "Sentiment Delta",
        data: signedScores,
        borderColor: color,
        backgroundColor: gradientColor,
        borderWidth: 1.5,
        tension: 0.2,
        pointRadius: 2,
        pointHoverRadius: 4,
        pointBackgroundColor: color,
        fill: true,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#070b12",
        borderColor: "rgba(255, 255, 255, 0.14)",
        borderWidth: 1,
        titleColor: "#94a3b8",
        bodyColor: "#f8fafc",
        titleFont: { family: "monospace", size: 10 },
        bodyFont: { family: "monospace", size: 11 },
        padding: 6,
        displayColors: false,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: "#64748b", font: { family: "monospace", size: 9 }, maxTicksLimit: 5 },
      },
      y: {
        min: -1,
        max: 1,
        position: "right",
        grid: { color: "rgba(255, 255, 255, 0.04)" },
        ticks: { color: "#64748b", font: { family: "monospace", size: 9 }, stepSize: 0.5 },
      },
    },
  };

  return (
    <div className="terminal-card p-3.5 h-[240px] flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs font-bold text-white tracking-wider">
          AI SENTIMENT OSCILLATOR
        </span>
        <span
          className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
            trendUp ? "bg-emerald-500/10 text-emerald-400" : "bg-coral-500/10 text-coral-400"
          }`}
        >
          {trendUp ? "BULLISH BIAS" : "BEARISH BIAS"}
        </span>
      </div>
      <div className="flex-1 w-full min-h-0">
        <Line data={data} options={options} />
      </div>
    </div>
  );
}
