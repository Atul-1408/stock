import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
} from "chart.js";
import { Line } from "react-chartjs-2";
import { motion } from "framer-motion";
import { TrendingUp } from "lucide-react";
import { sentimentLabelToSignedScore } from "../utils/sentiment";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

function PriceChart({ prices, sentiments }) {
  if (!prices || prices.length === 0) {
    return (
      <div className="card p-8 h-[320px] flex flex-col items-center justify-center border-dashed border-2">
        <TrendingUp className="w-12 h-12 text-slate-400 mb-4 opacity-40" />
        <p className="text-slate-500 font-medium">No price data available for visualization.</p>
      </div>
    );
  }

  const sortedPrices = [...prices].sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
  const sentimentByDay = sentiments.reduce((acc, row) => {
    const key = (row.analyzed_at || row.published_at || "").slice(0, 10);
    if (!key) return acc;

    const signed = sentimentLabelToSignedScore(row.sentiment_label, row.sentiment_score);
    if (!acc[key]) acc[key] = [];
    acc[key].push(signed);
    return acc;
  }, {});

  const labels = sortedPrices.map((row) => row.trade_date);
  const closeData = sortedPrices.map((row) => row.close);
  const sentimentOverlay = labels.map((day) => {
    const dayScores = sentimentByDay[day] || [];
    if (dayScores.length === 0) return null;
    const avg = dayScores.reduce((sum, value) => sum + value, 0) / dayScores.length;
    return avg;
  });

  const data = {
    labels,
    datasets: [
      {
        label: "Market Price",
        data: closeData,
        yAxisID: "y",
        borderColor: "rgba(56, 189, 248, 1)",
        backgroundColor: "rgba(56, 189, 248, 0.1)",
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 6,
        fill: true,
      },
      {
        label: "AI Sentiment",
        data: sentimentOverlay,
        yAxisID: "y1",
        borderColor: "rgba(148, 163, 184, 0.4)",
        borderDash: [5, 5],
        tension: 0.4,
        pointRadius: 0,
        fill: false,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        position: 'top',
        align: 'end',
        labels: { boxWidth: 10, usePointStyle: true, color: "#64748b", font: { size: 10, weight: 'bold' } }
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        padding: 12,
        cornerRadius: 12,
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: "#64748b", font: { size: 10 } }
      },
      y: {
        position: "left",
        grid: { color: "rgba(148, 163, 184, 0.05)" },
        ticks: { color: "#64748b" },
      },
      y1: {
        position: "right",
        min: -1,
        max: 1,
        grid: { display: false },
        ticks: { display: false },
      },
    },
  };

  return (
    <motion.section
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.4 }}
      className="card p-6 h-[380px]"
    >
      <h2 className="text-sm font-black text-slate-500 uppercase tracking-widest mb-6">Price vs AI Sentiment Analysis</h2>
      <div className="h-[280px]">
        <Line data={data} options={options} />
      </div>
    </motion.section>
  );
}

export default PriceChart;

