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
import { BarChart3 } from "lucide-react";
import { sentimentLabelToSignedScore } from "../utils/sentiment";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

function SentimentChart({ sentiments }) {
  if (!sentiments || sentiments.length === 0) {
    return (
      <div className="card p-8 h-[320px] flex flex-col items-center justify-center border-dashed border-2">
        <BarChart3 className="w-12 h-12 text-slate-400 mb-4 opacity-40" />
        <p className="text-slate-500 font-medium">No sentiment data to visualize.</p>
      </div>
    );
  }

  const sorted = [...sentiments].sort((a, b) =>
    new Date(a.analyzed_at || a.published_at) - new Date(b.analyzed_at || b.published_at)
  );

  const labels = sorted.map((row) => (row.analyzed_at || row.published_at || "").slice(0, 10));
  const signedScores = sorted.map((row) =>
    sentimentLabelToSignedScore(row.sentiment_label, row.sentiment_score)
  );

  const trendUp = signedScores.length > 1
    ? signedScores[signedScores.length - 1] - signedScores[0] >= 0
    : true;

  const color = trendUp ? "rgba(16, 185, 129, 1)" : "rgba(244, 63, 94, 1)";
  const gradientColor = trendUp ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)";

  const data = {
    labels,
    datasets: [
      {
        label: "AI Sentiment Score",
        data: signedScores,
        borderColor: color,
        backgroundColor: gradientColor,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: color,
        fill: true,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#94a3b8',
        bodyColor: '#f1f5f9',
        padding: 12,
        cornerRadius: 12,
        displayColors: false
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: "#64748b", font: { size: 10 } }
      },
      y: {
        min: -1,
        max: 1,
        grid: { color: "rgba(148, 163, 184, 0.1)" },
        ticks: { color: "#64748b", stepSize: 0.5 },
      },
    },
  };

  return (
    <motion.section
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 }}
      className="card p-6 h-[380px]"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-sm font-black text-slate-500 uppercase tracking-widest">Sentiment Trend Analysis</h2>
        <div className={`px-3 py-1 rounded-full text-[10px] font-bold ${trendUp ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
          {trendUp ? '📈 UPWARD TREND' : '📉 DOWNWARD TREND'}
        </div>
      </div>
      <div className="h-[280px]">
        <Line data={data} options={options} />
      </div>
    </motion.section>
  );
}

export default SentimentChart;

