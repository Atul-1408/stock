import React, { useState } from 'react';
import { X, Minus, Plus, Loader2 } from 'lucide-react';
import api from '../utils/api';
import { toast } from 'react-toastify';

const OrderWindow = ({ stock, side: initialSide, onClose, onOrderPlaced }) => {
    const [side, setSide] = useState(initialSide || 'BUY');
    const [orderType, setOrderType] = useState('MARKET');
    const [productType, setProductType] = useState('CNC');
    const [quantity, setQuantity] = useState(1);
    const [price, setPrice] = useState(stock.last_price || 0);
    const [triggerPrice, setTriggerPrice] = useState('');
    const [validity, setValidity] = useState('DAY');
    const [loading, setLoading] = useState(false);

    const isBuy = side === 'BUY';
    const accent = isBuy ? 'emerald' : 'red';
    const ltp = stock.last_price || price;
    const totalAmount = quantity * (orderType === 'MARKET' ? ltp : price);

    const handleSubmit = async () => {
        setLoading(true);
        try {
            await api.post('/orders', {
                symbol: stock.symbol,
                side,
                order_type: orderType,
                product_type: productType,
                quantity,
                price: orderType !== 'MARKET' ? price : null,
                trigger_price: (orderType === 'SL' || orderType === 'SL-M') ? triggerPrice : null,
                validity,
            });
            toast.success(`${side} order placed for ${stock.symbol}`);
            onOrderPlaced?.();
            onClose?.();
        } catch (err) {
            toast.error(err.response?.data?.message || 'Order failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-white/5 dark:bg-slate-800/50 backdrop-blur-sm border border-white/10 rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <div>
                    <span className="text-white font-bold text-sm">{stock.symbol.replace('.NS', '')}</span>
                    <span className="text-gray-400 text-xs ml-2">{stock.exchange}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-white font-bold">
                        {stock.currency === 'INR' ? '₹' : '$'}{Number(ltp).toFixed(2)}
                    </span>
                    <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg transition-colors">
                        <X className="w-4 h-4 text-gray-400" />
                    </button>
                </div>
            </div>

            <div className="p-4 space-y-4">
                {/* Buy / Sell Toggle */}
                <div className="grid grid-cols-2 gap-1 bg-white/5 p-1 rounded-xl">
                    <button
                        onClick={() => setSide('BUY')}
                        className={`py-2 rounded-lg text-sm font-bold transition-all ${isBuy ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/25' : 'text-gray-400 hover:text-gray-200'
                            }`}
                    >BUY</button>
                    <button
                        onClick={() => setSide('SELL')}
                        className={`py-2 rounded-lg text-sm font-bold transition-all ${!isBuy ? 'bg-red-500 text-white shadow-lg shadow-red-500/25' : 'text-gray-400 hover:text-gray-200'
                            }`}
                    >SELL</button>
                </div>

                {/* Order Type */}
                <div className="grid grid-cols-4 gap-1 bg-white/5 p-1 rounded-xl">
                    {['MARKET', 'LIMIT', 'SL', 'SL-M'].map(t => (
                        <button
                            key={t}
                            onClick={() => setOrderType(t)}
                            className={`py-1.5 rounded-lg text-xs font-bold transition-all ${orderType === t ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
                                }`}
                        >{t}</button>
                    ))}
                </div>

                {/* Product Type */}
                <div>
                    <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1 block">Product</label>
                    <div className="grid grid-cols-3 gap-1 bg-white/5 p-1 rounded-xl">
                        {[
                            { value: 'CNC', label: 'Delivery' },
                            { value: 'MIS', label: 'Intraday' },
                            { value: 'NRML', label: 'Normal' },
                        ].map(p => (
                            <button
                                key={p.value}
                                onClick={() => setProductType(p.value)}
                                className={`py-1.5 rounded-lg text-xs font-bold transition-all ${productType === p.value ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'
                                    }`}
                            >{p.label}</button>
                        ))}
                    </div>
                </div>

                {/* Quantity */}
                <div>
                    <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1 block">Quantity</label>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setQuantity(q => Math.max(1, q - 1))}
                            className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                        ><Minus className="w-4 h-4 text-gray-400" /></button>
                        <input
                            type="number"
                            value={quantity}
                            onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                            className="flex-1 bg-white/5 border border-white/10 rounded-xl py-2 px-3 text-center text-white font-bold text-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                            min="1"
                        />
                        <button
                            onClick={() => setQuantity(q => q + 1)}
                            className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                        ><Plus className="w-4 h-4 text-gray-400" /></button>
                    </div>
                </div>

                {/* Price (for LIMIT / SL orders) */}
                {orderType !== 'MARKET' && (
                    <div>
                        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1 block">Price</label>
                        <input
                            type="number"
                            step="0.01"
                            value={price}
                            onChange={e => setPrice(parseFloat(e.target.value) || 0)}
                            className="w-full bg-white/5 border border-white/10 rounded-xl py-2 px-3 text-white font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                        />
                    </div>
                )}

                {/* Trigger Price (for SL / SL-M) */}
                {(orderType === 'SL' || orderType === 'SL-M') && (
                    <div>
                        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1 block">Trigger Price</label>
                        <input
                            type="number"
                            step="0.01"
                            value={triggerPrice}
                            onChange={e => setTriggerPrice(parseFloat(e.target.value) || 0)}
                            className="w-full bg-white/5 border border-white/10 rounded-xl py-2 px-3 text-white font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                        />
                    </div>
                )}

                {/* Validity */}
                <div className="flex gap-2">
                    {['DAY', 'IOC'].map(v => (
                        <button
                            key={v}
                            onClick={() => setValidity(v)}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all ${validity === v ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'bg-white/5 text-gray-400 border border-white/10'
                                }`}
                        >{v === 'DAY' ? 'Day' : 'IOC'}</button>
                    ))}
                </div>

                {/* Summary */}
                <div className="bg-white/5 rounded-xl p-3 space-y-2">
                    <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Est. Amount</span>
                        <span className="text-white font-bold">{stock.currency === 'INR' ? '₹' : '$'}{totalAmount.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Order</span>
                        <span className="text-gray-300">{orderType} • {productType} • {validity}</span>
                    </div>
                </div>

                {/* Submit */}
                <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className={`w-full py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${isBuy
                            ? 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-500/25'
                            : 'bg-red-500 hover:bg-red-400 text-white shadow-lg shadow-red-500/25'
                        } disabled:opacity-50`}
                >
                    {loading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        `${side} ${quantity} × ${stock.symbol.replace('.NS', '')} @ ${orderType === 'MARKET' ? 'MARKET' : price}`
                    )}
                </button>
            </div>
        </div>
    );
};

export default OrderWindow;
