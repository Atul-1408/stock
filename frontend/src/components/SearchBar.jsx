import { useState } from "react";
import { Search } from "lucide-react";
import { motion } from "framer-motion";

function SearchBar({ onSearch, loading }) {
  const [ticker, setTicker] = useState("");
  const [error, setError] = useState("");

  const validate = (val) => {
    const clean = val.trim().toUpperCase();
    if (!clean) return "Ticker is required";
    if (clean.length > 10) return "Ticker too long";
    if (/[^A-Z0-9.-]/.test(clean)) return "Invalid characters";
    return "";
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const validationError = validate(ticker);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    onSearch(ticker);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="card p-4 md:p-6"
    >
      <form onSubmit={handleSubmit} className="relative">
        <label htmlFor="ticker-input" className="block text-sm font-semibold text-slate-500 dark:text-slate-400 mb-3 ml-1 uppercase tracking-wider">
          Market Search
        </label>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-accent transition-colors" />
            <input
              id="ticker-input"
              value={ticker}
              onChange={(e) => {
                setTicker(e.target.value);
                if (error) setError("");
              }}
              placeholder="e.g. AAPL, TSLA, RELIANCE.NS"
              className={`w-full rounded-2xl border ${error ? 'border-rose-500' : 'border-slate-200 dark:border-slate-800'} bg-slate-50 dark:bg-slate-950/50 pl-11 pr-4 py-4 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all shadow-sm`}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex min-w-[140px] justify-center items-center rounded-2xl bg-accent text-slate-950 font-bold px-8 py-4 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-opacity-90 transform active:scale-95 transition-all shadow-lg shadow-accent/20"
          >
            {loading ? (
              <div className="h-5 w-5 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        </div>
        {error && (
          <motion.p
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-3 text-sm text-rose-500 font-medium ml-1"
          >
            {error}
          </motion.p>
        )}
      </form>
    </motion.div>
  );
}

export default SearchBar;

