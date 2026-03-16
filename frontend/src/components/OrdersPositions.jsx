import React, { useState, useEffect, useCallback } from 'react';
import { ClipboardList, BarChart3, Briefcase, XCircle, RefreshCw } from 'lucide-react';
import api from '../utils/api';
import { useCurrency } from '../contexts/CurrencyContext';
import { formatCurrency } from '../utils/currency';
import { toast } from 'react-toastify';

const OrdersPositions = () => {
    const { currency } = useCurrency();
    const [activeTab, setActiveTab] = useState('orders');
    const [orders, setOrders] = useState([]);
    const [positions, setPositions] = useState([]);
    const [totalPnl, setTotalPnl] = useState(0);
    const [loading, setLoading] = useState(false);

    const fetchOrders = useCallback(async () => {
        try {
            const { data } = await api.get('/orders/list');
            setOrders(data.orders || []);
        } catch (err) {
            console.error('Error fetching orders:', err);
        }
    }, []);

    const fetchPositions = useCallback(async () => {
        try {
            const { data } = await api.get('/positions');
            setPositions(data.positions || []);
            setTotalPnl(data.total_pnl || 0);
        } catch (err) {
            console.error('Error fetching positions:', err);
        }
    }, []);

    useEffect(() => {
        if (activeTab === 'orders') fetchOrders();
        else if (activeTab === 'positions') fetchPositions();
    }, [activeTab, fetchOrders, fetchPositions]);

    const cancelOrder = async (orderId) => {
        try {
            await api.delete(`/orders/${orderId}/cancel`);
            toast.success('Order cancelled');
            fetchOrders();
        } catch (err) {
            toast.error('Failed to cancel order');
        }
    };

    const tabs = [
        { id: 'orders', label: 'Orders', icon: <ClipboardList className="w-4 h-4" />, count: orders.length },
        { id: 'positions', label: 'Positions', icon: <BarChart3 className="w-4 h-4" />, count: positions.length },
    ];

    return (
        <div className="bg-white/5 dark:bg-slate-800/30 backdrop-blur-sm border border-white/10 rounded-2xl overflow-hidden">
            {/* Tab Headers */}
            <div className="flex items-center border-b border-white/10">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-5 py-3 text-sm font-bold transition-all border-b-2 ${activeTab === tab.id
                            ? 'text-blue-400 border-blue-500'
                            : 'text-gray-400 border-transparent hover:text-gray-200'
                            }`}
                    >
                        {tab.icon}
                        {tab.label}
                        {tab.count > 0 && (
                            <span className="ml-1 px-1.5 py-0.5 bg-white/10 rounded-md text-[10px]">{tab.count}</span>
                        )}
                    </button>
                ))}

                <div className="ml-auto pr-3">
                    <button
                        onClick={() => activeTab === 'orders' ? fetchOrders() : fetchPositions()}
                        className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <RefreshCw className="w-4 h-4 text-gray-400" />
                    </button>
                </div>
            </div>

            {/* Orders Tab */}
            {activeTab === 'orders' && (
                <div className="overflow-x-auto">
                    {orders.length === 0 ? (
                        <div className="text-center py-12 text-gray-400 text-sm">No orders yet. Place an order from the market watch.</div>
                    ) : (
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-white/5">
                                    <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Time</th>
                                    <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Symbol</th>
                                    <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Side</th>
                                    <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Type</th>
                                    <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Qty</th>
                                    <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Price</th>
                                    <th className="text-center py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Status</th>
                                    <th className="text-center py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.map(order => (
                                    <tr key={order.id} className="border-b border-white/5 hover:bg-white/5">
                                        <td className="py-2.5 px-4 text-gray-400 text-xs">
                                            {new Date(order.created_at).toLocaleTimeString()}
                                        </td>
                                        <td className="py-2.5 px-4">
                                            <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-xs font-bold">
                                                {order.symbol.replace('.NS', '')}
                                            </span>
                                        </td>
                                        <td className="py-2.5 px-4">
                                            <span className={`px-2 py-0.5 rounded text-xs font-bold ${order.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                                                }`}>{order.side}</span>
                                        </td>
                                        <td className="py-2.5 px-4 text-gray-300 text-xs">{order.order_type} • {order.product_type}</td>
                                        <td className="py-2.5 px-4 text-right text-white font-medium">{order.quantity}</td>
                                        <td className="py-2.5 px-4 text-right text-white font-medium">
                                            {order.filled_price ? formatCurrency(order.filled_price, currency) : order.price ? formatCurrency(order.price, currency) : 'MKT'}
                                        </td>
                                        <td className="py-2.5 px-4 text-center">
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${order.status === 'FILLED' ? 'bg-emerald-500/10 text-emerald-400' :
                                                order.status === 'OPEN' ? 'bg-yellow-500/10 text-yellow-400' :
                                                    order.status === 'CANCELLED' ? 'bg-gray-500/10 text-gray-400' :
                                                        'bg-white/10 text-gray-400'
                                                }`}>{order.status}</span>
                                        </td>
                                        <td className="py-2.5 px-4 text-center">
                                            {order.status === 'OPEN' && (
                                                <button
                                                    onClick={() => cancelOrder(order.id)}
                                                    className="p-1 hover:bg-red-500/10 text-red-400 rounded-lg transition-colors"
                                                    title="Cancel Order"
                                                >
                                                    <XCircle className="w-4 h-4" />
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Positions Tab */}
            {activeTab === 'positions' && (
                <div className="overflow-x-auto">
                    {positions.length === 0 ? (
                        <div className="text-center py-12 text-gray-400 text-sm">No open positions.</div>
                    ) : (
                        <>
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-white/5">
                                        <th className="text-left py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Symbol</th>
                                        <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Qty</th>
                                        <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Avg Price</th>
                                        <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase">LTP</th>
                                        <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase">P&L</th>
                                        <th className="text-right py-3 px-4 text-gray-400 text-xs font-semibold uppercase">Value</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {positions.map(pos => (
                                        <tr key={pos.symbol} className="border-b border-white/5 hover:bg-white/5">
                                            <td className="py-2.5 px-4">
                                                <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-xs font-bold">
                                                    {pos.symbol.replace('.NS', '')}
                                                </span>
                                            </td>
                                            <td className="py-2.5 px-4 text-right text-white font-medium">{pos.quantity}</td>
                                            <td className="py-2.5 px-4 text-right text-gray-300">{formatCurrency(pos.avg_price, currency)}</td>
                                            <td className="py-2.5 px-4 text-right text-white font-bold">{formatCurrency(pos.ltp, currency)}</td>
                                            <td className="py-2.5 px-4 text-right">
                                                <span className={`font-bold ${pos.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                    {pos.pnl >= 0 ? '+' : ''}{pos.pnl.toFixed(2)} ({pos.pnl_pct.toFixed(2)}%)
                                                </span>
                                            </td>
                                            <td className="py-2.5 px-4 text-right text-gray-300">{formatCurrency(pos.current_value, currency)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            <div className="flex justify-end px-4 py-3 border-t border-white/10">
                                <span className="text-sm text-gray-400 mr-2">Total P&L:</span>
                                <span className={`text-sm font-bold ${totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {totalPnl >= 0 ? '+' : ''}{formatCurrency(Math.abs(totalPnl), currency)}
                                </span>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default OrdersPositions;
