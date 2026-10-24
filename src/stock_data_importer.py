"""Stock Data Importer — populates the stock_universe with real stocks.

Imports US stocks (top NASDAQ/NYSE), Indian stocks (NIFTY 50 + popular),
and top cryptocurrencies using yfinance.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import yfinance as yf
import database

# ==========================================
# STOCK LISTS
# ==========================================

# Top US stocks (NASDAQ + NYSE blue chips)
US_STOCKS = [
    # NASDAQ mega caps
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST',
    'NFLX', 'AMD', 'ADBE', 'PEP', 'CSCO', 'INTC', 'CMCSA', 'QCOM', 'TXN', 'INTU',
    'AMGN', 'ISRG', 'AMAT', 'ADP', 'GILD', 'ADI', 'LRCX', 'REGN', 'VRTX', 'BKNG',
    'MU', 'PANW', 'SNPS', 'CDNS', 'MELI', 'PYPL', 'KLAC', 'MNST', 'ORLY', 'FTNT',
    'MDLZ', 'MRVL', 'CTAS', 'DXCM', 'MAR', 'ABNB', 'CHTR', 'TEAM', 'CRWD', 'WDAY',
    # NYSE blue chips
    'BRK-B', 'JPM', 'V', 'UNH', 'JNJ', 'WMT', 'XOM', 'MA', 'PG', 'HD',
    'CVX', 'MRK', 'ABBV', 'LLY', 'BAC', 'KO', 'CRM', 'TMO', 'MCD', 'ACN',
    'ABT', 'DHR', 'LIN', 'VZ', 'DIS', 'NEE', 'PM', 'IBM', 'HON', 'RTX',
    'AXP', 'SPGI', 'CAT', 'GS', 'LOW', 'DE', 'SYK', 'BLK', 'MS', 'BA',
    'ELV', 'SBUX', 'PLD', 'UPS', 'LMT', 'GE', 'MMM', 'NKE', 'T', 'WFC',
    'C', 'ORCL', 'CB', 'SO', 'DUK', 'BMY', 'PFE', 'COP', 'EOG', 'SLB',
    'F', 'GM', 'DAL', 'UAL', 'AAL', 'UBER', 'LYFT', 'SQ', 'COIN', 'HOOD',
]

# Indian stocks (NSE) — NIFTY 50 + popular midcaps
INDIAN_STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
    'ICICIBANK.NS', 'KOTAKBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS',
    'AXISBANK.NS', 'LT.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS', 'MARUTI.NS',
    'TITAN.NS', 'SUNPHARMA.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS', 'WIPRO.NS',
    'HCLTECH.NS', 'TECHM.NS', 'POWERGRID.NS', 'NTPC.NS', 'M&M.NS',
    'TATASTEEL.NS', 'BAJAJFINSV.NS', 'ONGC.NS', 'DRREDDY.NS', 'ADANIPORTS.NS',
    'COALINDIA.NS', 'DIVISLAB.NS', 'GRASIM.NS', 'HINDALCO.NS', 'INDUSINDBK.NS',
    'JSWSTEEL.NS', 'TATAMOTORS.NS', 'BRITANNIA.NS', 'CIPLA.NS', 'EICHERMOT.NS',
    'HEROMOTOCO.NS', 'APOLLOHOSP.NS', 'BPCL.NS', 'IOC.NS', 'TATACONSUM.NS',
    'SHREECEM.NS', 'SBILIFE.NS', 'HDFCLIFE.NS', 'ADANIENT.NS', 'ADANIGREEN.NS',
    'ZOMATO.NS', 'VEDL.NS', 'SAIL.NS', 'NMDC.NS', 'GODREJCP.NS',
    'MARICO.NS', 'DABUR.NS', 'PIDILITIND.NS', 'HAVELLS.NS', 'VOLTAS.NS',
    'DMART.NS', 'JUBLFOOD.NS', 'HAL.NS', 'BEL.NS', 'DLF.NS',
    'POLYCAB.NS', 'TRENT.NS', 'IRFC.NS', 'PFC.NS', 'RECLTD.NS',
    'YESBANK.NS', 'BANKBARODA.NS', 'PNB.NS', 'CANBK.NS', 'SIEMENS.NS',
]

# Cryptocurrencies
CRYPTO_SYMBOLS = [
    'BTC-USD', 'ETH-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD',
    'SOL-USD', 'DOGE-USD', 'DOT-USD', 'MATIC-USD', 'SHIB-USD',
    'AVAX-USD', 'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD',
]

# Market indices
INDEX_SYMBOLS = {
    '^NSEI': ('NIFTY50', 'NIFTY 50'),
    '^BSESN': ('SENSEX', 'BSE SENSEX'),
    '^GSPC': ('SP500', 'S&P 500'),
    '^IXIC': ('NASDAQ', 'NASDAQ Composite'),
    '^DJI': ('DOW', 'Dow Jones'),
    '^FTSE': ('FTSE100', 'FTSE 100'),
}


def import_stocks_batch(symbols, exchange, country, currency):
    """Import a batch of stocks using yfinance."""
    stocks_data = []
    total = len(symbols)

    for i, symbol in enumerate(symbols):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            stocks_data.append({
                'symbol': symbol,
                'company_name': info.get('longName') or info.get('shortName') or symbol,
                'exchange': exchange,
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap'),
                'country': country,
                'currency': currency,
            })

            # Also import fundamentals
            database.upsert_fundamentals({
                'symbol': symbol,
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'eps': info.get('trailingEps'),
                'book_value': info.get('bookValue'),
                'face_value': info.get('faceValue'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'avg_volume_30d': info.get('averageVolume'),
                'shares_outstanding': info.get('sharesOutstanding'),
            })

            if (i + 1) % 10 == 0:
                print(f"  [{exchange}] {i + 1}/{total} imported...")

        except Exception as e:
            print(f"  Warning: Skipping {symbol}: {e}")
            continue

    count = database.bulk_insert_stocks(stocks_data)
    return count


def import_market_data_batch(symbols):
    """Fetch and cache current market data for a list of symbols."""
    from datetime import datetime
    imported = 0

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='2d', interval='1d')

            if hist.empty or len(hist) < 1:
                continue

            latest = hist.iloc[-1]
            prev_close = float(hist.iloc[-2]['Close']) if len(hist) >= 2 else float(latest['Close'])
            last_price = float(latest['Close'])
            change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close > 0 else 0

            database.upsert_market_cache({
                'symbol': symbol,
                'last_price': last_price,
                'open_price': float(latest['Open']),
                'high_price': float(latest['High']),
                'low_price': float(latest['Low']),
                'prev_close': prev_close,
                'volume': int(latest['Volume']),
                'change_pct': round(change_pct, 4),
                'last_trade_time': datetime.now().isoformat(),
            })
            imported += 1

        except Exception:
            continue

    return imported


def import_indices():
    """Import major market indices."""
    from datetime import datetime
    print("Importing market indices...")

    for yf_symbol, (index_name, display_name) in INDEX_SYMBOLS.items():
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
            print(f"  {display_name}: {current:,.2f} ({change_pct:+.2f}%)")

        except Exception as e:
            print(f"  Warning: Skipping {display_name}: {e}")

    print("Done importing indices.")


def run_full_import():
    """Run the full stock data import."""
    database.init_db()

    print("=" * 60)
    print("STOCK DATA IMPORTER")
    print("=" * 60)

    # US Stocks
    print(f"\n[1/4] Importing {len(US_STOCKS)} US stocks...")
    us_count = import_stocks_batch(US_STOCKS, 'NASDAQ/NYSE', 'USA', 'USD')
    print(f"  Imported {us_count} US stocks.")

    # Indian Stocks
    print(f"\n[2/4] Importing {len(INDIAN_STOCKS)} Indian stocks...")
    in_count = import_stocks_batch(INDIAN_STOCKS, 'NSE', 'India', 'INR')
    print(f"  Imported {in_count} Indian stocks.")

    # Crypto
    print(f"\n[3/4] Importing {len(CRYPTO_SYMBOLS)} cryptocurrencies...")
    crypto_count = import_stocks_batch(CRYPTO_SYMBOLS, 'CRYPTO', 'Global', 'USD')
    print(f"  Imported {crypto_count} cryptocurrencies.")

    # Indices
    print(f"\n[4/4] Importing market indices...")
    import_indices()

    # Cache market data for a subset of popular stocks
    print(f"\nCaching live market data for top stocks...")
    top_stocks = US_STOCKS[:30] + INDIAN_STOCKS[:20] + CRYPTO_SYMBOLS[:5]
    mkt_count = import_market_data_batch(top_stocks)
    print(f"  Cached market data for {mkt_count} symbols.")

    total = database.get_stock_universe_count()
    print(f"\n{'=' * 60}")
    print(f"IMPORT COMPLETE: {total} stocks in the universe")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_full_import()
