"""Price fetching module using yfinance."""

from typing import Dict, List

import pandas as pd
import yfinance as yf

from config import Config


def fetch_last_30_days_prices(ticker: str) -> List[Dict]:
    """Fetch recent daily OHLCV data for a ticker.

    Returns a list of dictionaries ready to store in SQLite.
    """
    df = yf.download(
        tickers=ticker,
        period=f"{Config.PRICE_LOOKBACK_DAYS}d",
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        return []

    # yfinance (v0.2+) returns MultiIndex columns. Flatten if necessary.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Ensure datetime index is standard and clean before converting to records.
    df = df.reset_index()

    # yfinance usually returns columns: Date, Open, High, Low, Close, Adj Close, Volume
    records = []
    for _, row in df.iterrows():
        trade_date = pd.to_datetime(row["Date"]).date().isoformat()
        records.append(
            {
                "trade_date": trade_date,
                "open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                "high": float(row["High"]) if pd.notna(row["High"]) else None,
                "low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                "adj_close": float(row["Adj Close"]) if pd.notna(row["Adj Close"]) else None,
                "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
            }
        )

    return records
