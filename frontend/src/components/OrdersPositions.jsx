import React, { useState, useEffect, useCallback } from "react";
import { ClipboardList, BarChart3, XCircle, RefreshCw, AlertTriangle } from "lucide-react";
import api from "../utils/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { formatCurrency } from "../utils/currency";
import { toast } from "react-toastify";

export default function OrdersPositions() {
  const { currency } = useCurrency();
  const [activeTab, setActiveTab] = useState("orders");
  const [orders, setOrders] = useState([]);
  const [positions, setPositions] = useState([]);
  const [totalPnl, setTotalPnl] = useState(0);
  const [loading, setLoading] = useState(false);
  const [cancellingId, setCancellingId] = useState(null);

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await api.get("/orders/list");
      setOrders(data.orders || []);
    } catch (err) {
      console.error("Error fetching orders:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPositions = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await api.get("/positions");
      setPositions(data.positions || []);
      setTotalPnl(data.total_pnl || 0);
    } catch (err) {
      console.error("Error fetching positions:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "orders") fetchOrders();
    else if (activeTab === "positions") fetchPositions();
  }, [activeTab, fetchOrders, fetchPositions]);

  const cancelOrder = async (orderId) => {
    if (!window.confirm(`Are you sure you want to cancel order #${orderId}?`)) {
      return;
    }
    try {
      setCancellingId(orderId);
      await api.delete(`/orders/${orderId}/cancel`);
      toast.success("Order cancelled");
      fetchOrders();
    } catch (err) {
      toast.error(err.response?.data?.message || "Failed to cancel order");
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="terminal-card overflow-hidden font-mono text-xs">
      {/* Tab Navigation Header */}
      <div className="flex items-center justify-between border-b border-white/10 px-3 bg-[#080d16]">
        <div className="flex items-center">
          <button
            onClick={() => setActiveTab("orders")}
            className={`flex items-center gap-2 px-4 py-3 font-bold border-b-2 transition-all ${
              activeTab === "orders"
                ? "text-cyan-400 border-cyan-400 bg-white/5"
                : "text-slate-400 border-transparent hover:text-white"
            }`}
          >
            <ClipboardList size={14} />
            <span>ORDERS</span>
            <span className="px-1.5 py-0.2 rounded text-[10px] bg-white/10 text-slate-300">
              {orders.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("positions")}
            className={`flex items-center gap-2 px-4 py-3 font-bold border-b-2 transition-all ${
              activeTab === "positions"
                ? "text-cyan-400 border-cyan-400 bg-white/5"
                : "text-slate-400 border-transparent hover:text-white"
            }`}
          >
            <BarChart3 size={14} />
            <span>POSITIONS</span>
            <span className="px-1.5 py-0.2 rounded text-[10px] bg-white/10 text-slate-300">
              {positions.length}
            </span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          {activeTab === "positions" && (
            <div className="text-[11px] font-bold">
              <span className="text-slate-500 mr-1.5">NET P&L:</span>
              <span className={totalPnl >= 0 ? "text-emerald-400" : "text-coral-400"}>
                {totalPnl >= 0 ? "+" : ""}${Number(totalPnl).toFixed(2)}
              </span>
            </div>
          )}

          <button
            onClick={() => (activeTab === "orders" ? fetchOrders() : fetchPositions())}
            disabled={loading}
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-white/5 transition-colors"
            title="Refresh Ledger"
          >
            <RefreshCw size={13} className={loading ? "animate-spin text-cyan-400" : ""} />
          </button>
        </div>
      </div>

      {/* Tab 1: Orders Table */}
      {activeTab === "orders" && (
        <div className="overflow-x-auto">
          {orders.length > 0 ? (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 text-[10px] text-slate-400 uppercase bg-[#090e17]">
                  <th className="py-2.5 px-3 font-semibold">TIME</th>
                  <th className="py-2.5 px-3 font-semibold">SYMBOL</th>
                  <th className="py-2.5 px-3 font-semibold">SIDE</th>
                  <th className="py-2.5 px-3 font-semibold">TYPE</th>
                  <th className="py-2.5 px-3 font-semibold text-right">QTY</th>
                  <th className="py-2.5 px-3 font-semibold text-right">PRICE</th>
                  <th className="py-2.5 px-3 font-semibold">STATUS</th>
                  <th className="py-2.5 px-3 font-semibold text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {orders.map((o) => {
                  const isBuy = o.side === "BUY";
                  const isFilled = o.status === "FILLED";
                  const isOpen = o.status === "OPEN";
                  const timeStr = o.created_at ? o.created_at.slice(11, 19) : "—";

                  return (
                    <tr key={o.id} className="hover:bg-white/5 transition-colors">
                      <td className="py-2.5 px-3 text-slate-400 text-[11px]">{timeStr}</td>
                      <td className="py-2.5 px-3 font-bold text-white">{o.symbol}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            isBuy ? "bg-emerald-500/10 text-emerald-400" : "bg-coral-500/10 text-coral-400"
                          }`}
                        >
                          {o.side}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 text-[11px]">{o.order_type}</td>
                      <td className="py-2.5 px-3 text-right text-slate-200">{Number(o.quantity).toLocaleString()}</td>
                      <td className="py-2.5 px-3 text-right text-slate-200">
                        {o.price != null ? `$${Number(o.price).toFixed(2)}` : "MKT"}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            isFilled
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : isOpen
                              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                              : "bg-slate-500/10 text-slate-400 border border-slate-500/20"
                          }`}
                        >
                          {o.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {isOpen ? (
                          <button
                            onClick={() => cancelOrder(o.id)}
                            disabled={cancellingId === o.id}
                            className="px-2 py-0.5 rounded bg-coral-500/10 text-coral-400 hover:bg-coral-500/20 text-[10px] font-bold border border-coral-500/20"
                          >
                            {cancellingId === o.id ? "..." : "CANCEL"}
                          </button>
                        ) : (
                          <span className="text-slate-600 text-[10px]">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="py-8 text-center text-slate-500">
              NO ORDERS RECORDED IN CURRENT SESSION
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Positions Table */}
      {activeTab === "positions" && (
        <div className="overflow-x-auto">
          {positions.length > 0 ? (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 text-[10px] text-slate-400 uppercase bg-[#090e17]">
                  <th className="py-2.5 px-3 font-semibold">SYMBOL</th>
                  <th className="py-2.5 px-3 font-semibold text-right">SHARES</th>
                  <th className="py-2.5 px-3 font-semibold text-right">AVG BUY</th>
                  <th className="py-2.5 px-3 font-semibold text-right">LTP</th>
                  <th className="py-2.5 px-3 font-semibold text-right">CURRENT VAL</th>
                  <th className="py-2.5 px-3 font-semibold text-right">P&L ($)</th>
                  <th className="py-2.5 px-3 font-semibold text-right">P&L (%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {positions.map((p) => {
                  const pnlUp = (p.pnl || 0) >= 0;
                  return (
                    <tr key={p.symbol} className="hover:bg-white/5 transition-colors">
                      <td className="py-2.5 px-3 font-bold text-white">{p.symbol}</td>
                      <td className="py-2.5 px-3 text-right text-slate-200">{Number(p.quantity).toLocaleString()}</td>
                      <td className="py-2.5 px-3 text-right text-slate-300">${Number(p.avg_price).toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right text-slate-300">${Number(p.ltp).toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right text-white font-bold">${Number(p.current_value).toFixed(2)}</td>
                      <td className={`py-2.5 px-3 text-right font-bold ${pnlUp ? "text-emerald-400" : "text-coral-400"}`}>
                        {pnlUp ? "+" : ""}${Number(p.pnl || 0).toFixed(2)}
                      </td>
                      <td className={`py-2.5 px-3 text-right font-bold ${pnlUp ? "text-emerald-400" : "text-coral-400"}`}>
                        {pnlUp ? "+" : ""}{Number(p.pnl_pct || 0).toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="py-8 text-center text-slate-500">
              NO OPEN POSITIONS HELD
            </div>
          )}
        </div>
      )}
    </div>
  );
}
