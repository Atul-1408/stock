import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { useCurrency, getNativeCurrency } from "../contexts/CurrencyContext";
import { getCurrencySymbol } from "../utils/currency";
import { tickerService } from "../services/TickerService";

const TAPE_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META", "AMZN", "NFLX",
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "TATASTEEL.NS",
    "SBIN.NS", "WIPRO.NS", "ICICIBANK.NS", "BAJFINANCE.NS", "ADANIENT.NS",
];

export default function TickerTape() {
    const { currency, convertPrice } = useCurrency();
    const sym = getCurrencySymbol(currency);
    const [items, setItems] = useState(
        TAPE_TICKERS.map((t) => ({ ticker: t, price: null, change: null, changePct: null }))
    );

    useEffect(() => {
        // Subscribe to ticker updates using the service
        const componentId = 'ticker-tape';
        
        const handleUpdate = (data) => {
            if (data?.length) {
                setItems(data);
            }
        };

        // Subscribe for updates
        tickerService.subscribe(componentId, handleUpdate, TAPE_TICKERS);

        // Cleanup
        return () => {
            tickerService.unsubscribe(componentId);
        };
    }, []);

    // Triplicate so the loop is seamless at any screen width
    const row = [...items, ...items, ...items];

    return (
        <div
            style={{
                background: "#0d1117",
                borderBottom: "1px solid rgba(0,255,136,0.15)",
                height: 40,
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                zIndex: 9999,
                width: "100%",
            }}
        >
            {/* Fade left */}
            <div style={{
                position: "absolute", left: 0, top: 0, height: "100%", width: 60,
                background: "linear-gradient(to right, #0d1117, transparent)",
                zIndex: 10, pointerEvents: "none",
            }} />
            {/* Fade right */}
            <div style={{
                position: "absolute", right: 0, top: 0, height: "100%", width: 60,
                background: "linear-gradient(to left, #0d1117, transparent)",
                zIndex: 10, pointerEvents: "none",
            }} />

            <div className="ticker-tape-track" style={{ animationDuration: `${row.length * 2.5}s` }}>
                {row.map((item, i) => {
                    const up = item.change === null ? null : item.change >= 0;
                    return (
                        <span
                            key={`${item.ticker}-${i}`}
                            style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6,
                                padding: "0 18px",
                                borderRight: "1px solid rgba(255,255,255,0.06)",
                                flexShrink: 0,
                            }}
                        >
                            <span style={{ fontWeight: 800, color: "#fff", fontSize: 12, letterSpacing: "0.03em" }}>
                                {item.ticker}
                            </span>
                            <span style={{ fontWeight: 700, color: "rgba(255,255,255,0.85)", fontSize: 12 }}>
                                {item.price != null ? `${sym}${Number(convertPrice(item.price, getNativeCurrency(item.ticker))).toFixed(2)}` : "—"}
                            </span>
                            {up !== null && (
                                <span style={{
                                    display: "inline-flex", alignItems: "center", gap: 2,
                                    fontSize: 11, fontWeight: 700,
                                    color: up ? "#34d399" : "#f87171",
                                }}>
                                    {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                                    {up ? "+" : ""}{Number(item.change).toFixed(2)}
                                    <span style={{ opacity: 0.65 }}>
                                        ({up ? "+" : ""}{Number(item.changePct).toFixed(2)}%)
                                    </span>
                                </span>
                            )}
                        </span>
                    );
                })}
            </div>
        </div>
    );
}
