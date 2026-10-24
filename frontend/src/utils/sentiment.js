export function sentimentLabelToSignedScore(label, score) {
  const safeScore = Number(score ?? 0);
  if (label === "Positive") return safeScore;
  if (label === "Negative") return -safeScore;
  return 0;
}

export function moodFromAverage(avg) {
  if (avg > 0.15) return {
    text: "BULLISH",
    icon: "🚀",
    tone: "text-emerald-600 dark:text-emerald-300 bg-emerald-500/10 dark:bg-emerald-500/20 border-emerald-500/20 dark:border-emerald-400/40"
  };
  if (avg < -0.15) return {
    text: "BEARISH",
    icon: "📉",
    tone: "text-rose-600 dark:text-rose-300 bg-rose-500/10 dark:bg-rose-500/20 border-rose-500/20 dark:border-rose-400/40"
  };
  return {
    text: "NEUTRAL",
    icon: "➖",
    tone: "text-slate-600 dark:text-slate-300 bg-slate-500/10 dark:bg-slate-500/20 border-slate-500/20 dark:border-slate-300/30"
  };
}
