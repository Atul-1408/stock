import { motion } from "framer-motion";
import { moodFromAverage } from "../utils/sentiment";

function MarketMood({ sentiments }) {
  if (!sentiments || sentiments.length === 0) return null;

  const totalScore = sentiments.reduce((sum, s) => {
    const safeScore = Number(s.sentiment_score ?? 0);
    if (s.sentiment_label === "Positive") return sum + safeScore;
    if (s.sentiment_label === "Negative") return sum - safeScore;
    return sum;
  }, 0);

  const average = totalScore / sentiments.length;
  const mood = moodFromAverage(average);

  return (
    <motion.section
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="card p-6 flex flex-col md:flex-row items-center justify-between gap-6 overflow-hidden relative"
    >
      <div className="relative z-10 w-full md:w-auto text-center md:text-left">
        <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-2 px-1">AI Market Sentiment</h2>
        <div className="flex flex-col md:flex-row items-center gap-2 md:gap-4">
          <span className="text-5xl md:text-6xl filter drop-shadow-sm">{mood.icon}</span>
          <span className={`text-4xl md:text-5xl font-black tracking-tighter ${mood.text === 'NEUTRAL' ? 'text-slate-400' : mood.text === 'BULLISH' ? 'text-emerald-500' : 'text-rose-500'
            }`}>
            {mood.text}
          </span>
        </div>
      </div>

      <div className={`px-10 py-5 rounded-[2rem] border min-w-[180px] text-center ${mood.tone} font-black text-2xl shadow-xl z-10 backdrop-blur-md`}>
        {average > 0 ? '+' : ''}{average.toFixed(2)}
      </div>

      {/* Modern Background Accents */}
      <div className={`absolute -right-12 -top-12 w-48 h-48 rounded-full blur-[80px] opacity-20 ${mood.text === 'BULLISH' ? 'bg-emerald-500' : mood.text === 'BEARISH' ? 'bg-rose-500' : 'bg-slate-500'
        }`} />
      <div className={`absolute -left-12 -bottom-12 w-48 h-48 rounded-full blur-[80px] opacity-10 ${mood.text === 'BULLISH' ? 'bg-cyan-500' : mood.text === 'BEARISH' ? 'bg-amber-500' : 'bg-indigo-500'
        }`} />
    </motion.section>
  );
}

export default MarketMood;
