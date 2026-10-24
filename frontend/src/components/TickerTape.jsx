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
        const componentId = "ticker-tape";
        const handleUpdate = (data) => {
            if (data?.length) {
                setItems(data);
            }
        };

        tickerService.subscribe(componentId, handleUpdate, TAPE_TICKERS);

        return () => {
            tickerService.unsubscribe(componentId);
        };
    }, []);

    const renderTickerGroup = (keyPrefix, isAriaHidden = false) => (
        <div
            className="flex items-center flex-shrink-0"
            aria-hidden={isAriaHidden ? "true" : undefined}
        >
            {items.map((item, i) => {
                const up = item.change === null ? null : item.change >= 0;
                return (
                    <span
                        key={`${keyPrefix}-${item.ticker}-${i}`}
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "0 14px",
                            borderRight: "1px solid rgba(255,255,255,0.06)",
                            flexShrink: 0,
                        }}
                    >
                        <span style={{ fontWeight: 800, color: "#f8fafc", fontSize: 11, letterSpacing: "0.04em" }}>
                            {item.ticker}
                        </span>
                        <span style={{ fontWeight: 600, color: "rgba(255,255,255,0.8)", fontSize: 11 }}>
                            {item.price != null
                                ? `${sym}${Number(convertPrice(item.price, getNativeCurrency(item.ticker))).toFixed(2)}`
                                : "—"}
                        </span>
                        {up !== null && (
                            <span
                                style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: 2,
                                    fontSize: 10,
                                    fontWeight: 700,
                                    color: up ? "#34d399" : "#fb7185",
                                }}
                            >
                                {up ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                                {up ? "+" : ""}{Number(item.change).toFixed(2)}
                            </span>
                        )}
                    </span>
                );
            })}
        </div>
    );

    return (
        <div
            style={{
                background: "#05080e",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                height: 32,
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
            className="font-mono select-none no-scrollbar"
            role="region"
            aria-label="Stock Price Ticker"
        >
            {/* Left fade gradient */}
            <div
                style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    height: "100%",
                    width: 48,
                    background: "linear-gradient(to right, #05080e, transparent)",
                    zIndex: 10,
                    pointerEvents: "none",
                }}
            />
            {/* Right fade gradient */}
            <div
                style={{
                    position: "absolute",
                    right: 0,
                    top: 0,
                    height: "100%",
                    width: 48,
                    background: "linear-gradient(to left, #05080e, transparent)",
                    zIndex: 10,
                    pointerEvents: "none",
                }}
            />

            {/* Seamless 2-group marquee track */}
            <div className="ticker-tape-track flex items-center no-scrollbar">
                {renderTickerGroup("primary", false)}
                {renderTickerGroup("duplicate", true)}
            </div>
        </div>
    );
}
