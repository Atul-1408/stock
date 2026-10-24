import React, { useState } from "react";
import { X, Minus, Plus, Loader2, ShieldCheck, AlertCircle } from "lucide-react";
import api from "../utils/api";
import { toast } from "react-toastify";

export default function OrderWindow({ stock, side: initialSide, onClose, onOrderPlaced }) {
  const [side, setSide] = useState(initialSide || "BUY");
  const [orderType, setOrderType] = useState("MARKET");
  const [productType, setProductType] = useState("CNC");
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState(stock.last_price || 0);
  const [triggerPrice, setTriggerPrice] = useState("");
  const [validity, setValidity] = useState("DAY");
  const [loading, setLoading] = useState(false);

  const isBuy = side === "BUY";
  const ltp = stock.last_price || price;
  const numQty = Math.max(1, parseInt(quantity, 10) || 1);
  const totalAmount = numQty * (orderType === "MARKET" ? ltp : price);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await api.post("/orders", {
        symbol: stock.symbol,
        side,
        order_type: orderType,
        product_type: productType,
        quantity: numQty,
        price: orderType !== "MARKET" ? parseFloat(price) : null,
        trigger_price: orderType === "SL" || orderType === "SL-M" ? parseFloat(triggerPrice) : null,
        validity,
      });
      toast.success(`${side} order submitted for ${stock.symbol}`);
      onOrderPlaced?.();
      onClose?.();
    } catch (err) {
      toast.error(err.response?.data?.message || "Order rejected by desk");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="terminal-card overflow-hidden font-mono border-cyan-500/30 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#090e17] border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-white font-bold text-sm tracking-wider">{stock.symbol}</span>
          <span className="text-cyan-400 text-[10px] bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
            {stock.exchange || "EQUITY"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-white font-bold text-xs">
            LTP: ${Number(ltp).toFixed(2)}
          </span>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-3.5">
        {/* Buy / Sell Action Selector */}
        <div className="grid grid-cols-2 gap-1.5 p-1 bg-black/40 rounded-lg border border-white/5">
          <button
            type="button"
            onClick={() => setSide("BUY")}
            className={`py-1.5 rounded text-xs font-bold transition-all ${
              isBuy ? "bg-emerald-500 text-black shadow-sm" : "text-slate-400 hover:text-white"
            }`}
          >
            BUY (LONG)
          </button>
          <button
            type="button"
            onClick={() => setSide("SELL")}
            className={`py-1.5 rounded text-xs font-bold transition-all ${
              !isBuy ? "bg-coral-500 text-white shadow-sm" : "text-slate-400 hover:text-white"
            }`}
          >
            SELL (SHORT)
          </button>
        </div>

        {/* Order Type */}
        <div>
          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">
            ORDER TYPE
          </label>
          <div className="grid grid-cols-4 gap-1 p-1 bg-black/40 rounded-lg border border-white/5">
            {["MARKET", "LIMIT", "SL", "SL-M"].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setOrderType(t)}
                className={`py-1 rounded text-[11px] font-bold transition-all ${
                  orderType === t ? "bg-white/15 text-white" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Product Type */}
        <div>
          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">
            PRODUCT
          </label>
          <div className="grid grid-cols-3 gap-1 p-1 bg-black/40 rounded-lg border border-white/5">
            {[
              { value: "CNC", label: "DELIVERY (CNC)" },
              { value: "MIS", label: "INTRADAY (MIS)" },
              { value: "NRML", label: "NORMAL (NRML)" },
            ].map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setProductType(p.value)}
                className={`py-1 rounded text-[10px] font-bold transition-all ${
                  productType === p.value ? "bg-white/15 text-white" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Quantity Field */}
        <div>
          <div className="flex justify-between text-[10px] text-slate-400 mb-1">
            <span>QUANTITY</span>
            <span className="text-slate-500">LOT SIZE: 1</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setQuantity(Math.max(1, numQty - 1))}
              className="p-2 rounded bg-white/5 hover:bg-white/10 text-slate-300 border border-white/5"
            >
              <Minus size={13} />
            </button>
            <input
              type="number"
              min="1"
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value, 10) || 1))}
              className="flex-1 bg-[#090e17] border border-white/10 rounded py-1.5 px-3 text-center text-xs text-white focus:outline-none focus:border-cyan-500/50"
            />
            <button
              type="button"
              onClick={() => setQuantity(numQty + 1)}
              className="p-2 rounded bg-white/5 hover:bg-white/10 text-slate-300 border border-white/5"
            >
              <Plus size={13} />
            </button>
          </div>
        </div>

        {/* Price Input (if not MARKET) */}
        {orderType !== "MARKET" && (
          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">
              LIMIT PRICE ($)
            </label>
            <input
              type="number"
              step="0.05"
              value={price}
              onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#090e17] border border-white/10 rounded py-1.5 px-3 text-xs text-white focus:outline-none focus:border-cyan-500/50"
            />
          </div>
        )}

        {/* Trigger Price (for SL / SL-M) */}
        {(orderType === "SL" || orderType === "SL-M") && (
          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">
              TRIGGER PRICE ($)
            </label>
            <input
              type="number"
              step="0.05"
              value={triggerPrice}
              onChange={(e) => setTriggerPrice(e.target.value)}
              className="w-full bg-[#090e17] border border-white/10 rounded py-1.5 px-3 text-xs text-white focus:outline-none focus:border-cyan-500/50"
            />
          </div>
        )}

        {/* Financial Summary */}
        <div className="p-2.5 rounded bg-black/40 border border-white/5 text-xs space-y-1">
          <div className="flex justify-between text-slate-400 text-[11px]">
            <span>ESTIMATED VALUE</span>
            <span className="text-white font-bold">${Number(totalAmount).toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-slate-400 text-[11px]">
            <span>VALIDITY</span>
            <span className="text-cyan-400 font-bold">{validity}</span>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="button"
          disabled={loading}
          onClick={handleSubmit}
          className={`w-full py-2.5 rounded text-xs font-bold uppercase tracking-wider transition-all disabled:opacity-50 flex items-center justify-center gap-2 ${
            isBuy
              ? "bg-emerald-500 hover:bg-emerald-400 text-black shadow-emerald-950/40"
              : "bg-coral-500 hover:bg-coral-400 text-white shadow-coral-950/40"
          }`}
        >
          {loading && <Loader2 size={13} className="animate-spin" />}
          <span>{side} {numQty} {stock.symbol} @ {orderType === "MARKET" ? "MKT" : `$${price}`}</span>
        </button>

        <div className="text-center text-[9px] text-slate-500">
          PAPER SIMULATION · ATOMIC EXECUTION CONFIRMATION
        </div>
      </div>
    </div>
  );
}
