import React, { useState, useEffect } from "react";
import { ShoppingCart, DollarSign, AlertCircle, CheckCircle2 } from "lucide-react";
import api from "../utils/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { formatCurrency } from "../utils/currency";

export default function TradingPanel({
  ticker,
  sentimentScore,
  sentimentLabel,
  currentPrice,
  onTradeSuccess,
  balance,
}) {
  const { currency } = useCurrency();
  const [shares, setShares] = useState(1);
  const [action, setAction] = useState("BUY");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  const numShares = Math.max(1, parseInt(shares, 10) || 1);
  const unitPrice = parseFloat(currentPrice) || 0.0;
  const totalCost = (numShares * unitPrice).toFixed(2);
  const canAfford = action === "BUY" ? (balance || 0) >= parseFloat(totalCost) : true;

  const handleTrade = async () => {
    if (numShares <= 0 || unitPrice <= 0) return;
    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const response = await api.post("/trade", {
        ticker,
        action,
        shares: numShares,
        sentiment_score: sentimentScore,
        sentiment_label: sentimentLabel,
      });

      setMessage({ type: "success", text: response.data.message });
      if (onTradeSuccess) onTradeSuccess(response.data.data);
      setShares(1);
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.message || "Trade execution failed.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (message.text) {
      const timer = setTimeout(() => setMessage({ type: "", text: "" }), 4000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  if (!ticker) return null;

  return (
    <div className="terminal-card p-4 font-mono space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <div className="flex items-center gap-2">
          <ShoppingCart size={14} className="text-cyan-400" />
          <span className="text-xs font-bold text-white tracking-wider">
            QUICK EXECUTION // {ticker}
          </span>
        </div>
        <span className="text-[10px] text-slate-400 font-semibold">
          LTP: ${unitPrice.toFixed(2)}
        </span>
      </div>

      {/* Action Toggle (BUY / SELL) */}
      <div className="grid grid-cols-2 gap-1.5 p-1 bg-black/40 rounded-lg border border-white/5">
        <button
          type="button"
          onClick={() => setAction("BUY")}
          className={`py-1.5 rounded text-xs font-bold transition-all ${
            action === "BUY"
              ? "bg-emerald-500 text-black shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          BUY (LONG)
        </button>
        <button
          type="button"
          onClick={() => setAction("SELL")}
          className={`py-1.5 rounded text-xs font-bold transition-all ${
            action === "SELL"
              ? "bg-coral-500 text-white shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          SELL (SHORT)
        </button>
      </div>

      {/* Quantity & Preset Chips */}
      <div>
        <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1">
          <span>SHARES</span>
          <span className="text-slate-500">MAX: 1,000,000</span>
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            min="1"
            value={shares}
            onChange={(e) => setShares(Math.max(1, parseInt(e.target.value, 10) || 1))}
            className="flex-1 bg-[#090e17] border border-white/10 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50"
          />
          <div className="flex gap-1">
            {[5, 10, 50, 100].map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => setShares(preset)}
                className="px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-[10px] text-slate-300 font-bold border border-white/5"
              >
                +{preset}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Box */}
      <div className="p-2.5 rounded bg-black/40 border border-white/5 text-xs space-y-1">
        <div className="flex justify-between text-[11px] text-slate-400">
          <span>ESTIMATED VALUE</span>
          <span className="text-white font-bold">${totalCost}</span>
        </div>
        <div className="flex justify-between text-[11px] text-slate-400">
          <span>PAPER CASH</span>
          <span className="text-emerald-400 font-bold">${Number(balance || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
        </div>
      </div>

      {/* Execution Feedback Message */}
      {message.text && (
        <div
          className={`p-2 rounded text-xs flex items-center gap-1.5 ${
            message.type === "success"
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "bg-coral-500/10 text-coral-400 border border-coral-500/20"
          }`}
        >
          {message.type === "success" ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
          <span className="truncate">{message.text}</span>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="button"
        disabled={loading || (action === "BUY" && !canAfford)}
        onClick={handleTrade}
        className={`w-full py-2 rounded text-xs font-bold uppercase tracking-wider transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
          action === "BUY"
            ? "bg-emerald-500 hover:bg-emerald-400 text-black shadow-emerald-950/40"
            : "bg-coral-500 hover:bg-coral-400 text-white shadow-coral-950/40"
        }`}
      >
        {loading
          ? "TRANSACTING..."
          : !canAfford && action === "BUY"
          ? "INSUFFICIENT FUNDS"
          : `${action} ${numShares} ${ticker}`}
      </button>

      <div className="text-center">
        <span className="text-[9px] text-slate-500">PAPER SIMULATION · ATOMIC EXECUTION</span>
      </div>
    </div>
  );
}
