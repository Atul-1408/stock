import { motion } from "framer-motion";
import { ExternalLink, Newspaper } from "lucide-react";

function NewsFeed({ news }) {
  if (!news || news.length === 0) {
    return (
      <div className="card p-8 text-center border-dashed border-2 bg-slate-500/5">
        <Newspaper className="w-12 h-12 text-slate-400 mx-auto mb-4 opacity-50" />
        <p className="text-slate-500 font-medium tracking-tight">No recent news available for this ticker.</p>
      </div>
    );
  }

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const item = {
    hidden: { opacity: 0, x: 20 },
    show: { opacity: 1, x: 0 }
  };

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-bold flex items-center gap-2 px-1 dark:text-slate-100">
        <Newspaper className="w-5 h-5 text-accent" />
        Latest Briefing
      </h2>
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="space-y-4"
      >
        {news.map((article, idx) => (
          <motion.div
            key={article.url || idx}
            variants={item}
            className="card group hover:border-accent/40 transition-all p-5"
          >
            <div className="flex justify-between items-start gap-4 mb-3">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-tighter ${article.sentiment_label === "Positive" ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" :
                  article.sentiment_label === "Negative" ? "bg-rose-500/10 text-rose-500 border border-rose-500/20" :
                    "bg-slate-500/10 text-slate-400 border border-slate-500/20"
                }`}>
                {article.sentiment_label || "Neutral"}
              </span>
              <span className="text-[10px] text-slate-500 font-semibold">{article.source}</span>
            </div>

            <h3 className="text-sm font-bold leading-snug group-hover:text-accent transition-colors dark:text-slate-200">
              {article.title}
            </h3>

            {article.url && (
              <a
                href={article.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 mt-4 text-xs font-bold text-slate-500 hover:text-accent transition-colors"
              >
                Read Article <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}

export default NewsFeed;
