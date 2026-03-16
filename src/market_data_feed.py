"""Market Data Feed — background thread that polls live prices.

Updates market_data_cache and market_indices in the database
at regular intervals using yfinance.
"""

import threading
import time
from datetime import datetime

import yfinance as yf
import database


class MarketDataFeed:
    """Background polling loop for live market data."""

    def __init__(self, stock_interval=30, index_interval=60):
        self.stock_interval = stock_interval  # seconds between stock price updates
        self.index_interval = index_interval  # seconds between index updates
        self._running = False
        self._thread = None

    def start(self):
        """Start the market data feed in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[MarketDataFeed] Started background price polling")

    def stop(self):
        self._running = False

    def _run(self):
        """Main polling loop."""
        tick = 0
        while self._running:
            try:
                # Update stock prices every stock_interval
                if tick % self.stock_interval == 0:
                    self._update_stock_prices()

                # Update indices every index_interval
                if tick % self.index_interval == 0:
                    self._update_indices()

            except Exception as e:
                print(f"[MarketDataFeed] Error: {e}")

            time.sleep(1)
            tick += 1

    def _update_stock_prices(self):
        """Fetch latest prices for stocks that have cached data."""
        try:
            symbols = self._get_cached_symbols()
            if not symbols:
                return

            # Batch download (yfinance supports multiple tickers)
            batch_size = 20
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                try:
                    data = yf.download(batch, period='2d', interval='1d', progress=False, group_by='ticker')

                    for symbol in batch:
                        try:
                            if len(batch) == 1:
                                df = data
                            else:
                                df = data[symbol] if symbol in data.columns.get_level_values(0) else None

                            if df is None or df.empty or len(df) < 1:
                                continue

                            close_vals = df['Close'].dropna()
                            if len(close_vals) < 1:
                                continue

                            last_price = float(close_vals.iloc[-1])
                            prev_close = float(close_vals.iloc[-2]) if len(close_vals) >= 2 else last_price
                            change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close > 0 else 0

                            database.upsert_market_cache({
                                'symbol': symbol,
                                'last_price': last_price,
                                'open_price': float(df['Open'].dropna().iloc[-1]) if not df['Open'].dropna().empty else None,
                                'high_price': float(df['High'].dropna().iloc[-1]) if not df['High'].dropna().empty else None,
                                'low_price': float(df['Low'].dropna().iloc[-1]) if not df['Low'].dropna().empty else None,
                                'prev_close': prev_close,
                                'volume': int(df['Volume'].dropna().iloc[-1]) if not df['Volume'].dropna().empty else 0,
                                'change_pct': round(change_pct, 4),
                                'last_trade_time': datetime.now().isoformat(),
                            })
                        except Exception:
                            continue
                except Exception:
                    continue

        except Exception as e:
            print(f"[MarketDataFeed] Stock price update error: {e}")

    def _update_indices(self):
        """Update major market indices."""
        INDEX_MAP = {
            '^NSEI': ('NIFTY50', 'NIFTY 50'),
            '^BSESN': ('SENSEX', 'BSE SENSEX'),
            '^GSPC': ('SP500', 'S&P 500'),
            '^IXIC': ('NASDAQ', 'NASDAQ Composite'),
            '^DJI': ('DOW', 'Dow Jones'),
        }

        for yf_symbol, (index_name, display_name) in INDEX_MAP.items():
            try:
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period='2d', interval='1d')

                if hist.empty:
                    continue

                latest = hist.iloc[-1]
                prev_close = float(hist.iloc[-2]['Close']) if len(hist) >= 2 else float(latest['Close'])
                current = float(latest['Close'])
                change_pct = ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0

                database.upsert_index({
                    'index_name': index_name,
                    'display_name': display_name,
                    'current_value': current,
                    'open_value': float(latest['Open']),
                    'high_value': float(latest['High']),
                    'low_value': float(latest['Low']),
                    'prev_close': prev_close,
                    'change_pct': round(change_pct, 4),
                })
            except Exception:
                continue

    def _get_cached_symbols(self):
        """Get list of symbols that have cached market data."""
        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol FROM market_data_cache LIMIT 100")
            return [row['symbol'] for row in cursor.fetchall()]


# Singleton instance
market_feed = MarketDataFeed(stock_interval=30, index_interval=60)
