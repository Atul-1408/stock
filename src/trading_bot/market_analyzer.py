import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta
from trading_bot import config

def fetch_data(ticker=config.TICKER, timeframe=config.TIMEFRAME, limit=config.LOOKBACK):
    """
    Fetches the latest market data using yfinance.
    Returns a DataFrame with OHLCV data.
    """
    try:
        # yfinance download options: period can be inferred or fixed. 
        # For '5m', we need '1d' or '5d' period to get enough intraday data, 
        # or use 'max' but limit rows.
        # 'limit' is essentially how many rows we keep, but we need to download enough first.
        # For 5m data, 5 days is plenty for 300 candles (12 candles/hr * 24hr * 5 = 1440).
        df = yf.download(ticker, period="5d", interval=timeframe, progress=False)
        
        if df.empty:
            print(f"[!] {ticker}: No data received. (Market likely closed or Ticker invalid). Waiting...")
            return None

        # Ensure columns are flat (yfinance sometimes returns MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            # yfinance returns (Price, Ticker) levels. We want to keep Price (Level 0).
            # So we drop Level 1 (Ticker).
            df.columns = df.columns.droplevel(1)
            
        # Rename lower case columns to Capitalized if needed or confirm standard yf names
        # Standard yf names: 'Open', 'High', 'Low', 'Close', 'Volume'
        # Keep last 'limit' rows
        df = df.tail(limit).copy()
        
        return df
    except Exception as e:
        print(f"Exception in fetch_data: {e}")
        return None

    except Exception as e:
        print(f"Exception in fetch_data: {e}")
        return None

def validate_ticker(ticker):
    """
    Fetches ticker info to verify identity.
    Returns: Long Name (str) or None
    """
    try:
        t = yf.Ticker(ticker)
        # Fast info fetch
        info = t.info
        long_name = info.get('longName', info.get('shortName', ticker))
        print(f"[OK] CONNECTED TO: {long_name} ({ticker})")
        return long_name
    except Exception as e:
        msg = str(e)
        # ignore crumb/401 messages because they are transient and clutter the log
        if 'Invalid Crumb' in msg or '401' in msg:
            print(f"[!] Temporary Yahoo Finance auth error for {ticker}, using ticker symbol")
        else:
            print(f"[!] Could not validate ticker {ticker}: {e}")
        return ticker

def get_daily_pivots(ticker=config.TICKER):
    """
    Fetches daily data to calculate Standard Floor Pivots.
    Returns: dict {P, R1, S1, R2, S2} or None
    """
    try:
        # Fetch last 2 days to ensure we have yesterday's closed candle
        daily = yf.download(ticker, period="5d", interval="1d", progress=False)
        
        if daily.empty or len(daily) < 2:
            return None
        
        # Flatten MultiIndex (Critical Fix for 'Same Numbers Glitch')
        if isinstance(daily.columns, pd.MultiIndex):
            daily.columns = daily.columns.droplevel(1)
            
        # Get 'Yesterday' - which is the second to last row (iloc[-2]) 
        # because iloc[-1] is 'Today' (live/incomplete).
        yesterday = daily.iloc[-2]
        
        H = yesterday['High']
        L = yesterday['Low']
        C = yesterday['Close']
        
        # Classic Pivot Formulas
        P = (H + L + C) / 3
        R1 = (2 * P) - L
        S1 = (2 * P) - H
        
        # Flatten if they are Series (yfinance weirdness)
        if isinstance(P, pd.Series): P = P.item()
        if isinstance(R1, pd.Series): R1 = R1.item()
        if isinstance(S1, pd.Series): S1 = S1.item()
        
        return {'P': P, 'R1': R1, 'S1': S1}
    except Exception as e:
        # print(f"Pivot Error: {e}") # Silent fail default
        return None

def detect_patterns(df):
    """
    Applies technical analysis to the DataFrame.
    Adds EMA and Pattern columns.
    """
    if df is None or len(df) < config.EMA_PERIOD:
        return df

    # Calculate EMA
    # pandas_ta extension appends to df if append=True
    # The column name will be 'EMA_200' usually or 'EMA_200'
    df.ta.ema(length=config.EMA_PERIOD, append=True)
    
    # We need to ensure the column is named 'EMA_200' for our logic.
    # by default it might be EMA_200.
    
    # Detect Patterns
    # cdl_pattern returns a DataFrame with columns like 'CDL_ENGULFING'
    # We append them.
    df.ta.cdl_pattern(name=['engulfing', 'hammer', 'shootingstar'], append=True)
    
    # Rename columns to standardized names expected by main.py and test_agent.py
    # Expected: 'ENGULFING', 'HAMMER', 'SHOOTING_STAR'
    # Created: 'CDL_ENGULFING', 'CDL_HAMMER', 'CDL_SHOOTINGSTAR' (Check capitalization)
    
    # Map them
    # Note: Column names are usually uppercase.
    rename_map = {
        'CDL_ENGULFING': 'ENGULFING',
        'CDL_HAMMER': 'HAMMER',
        'CDL_SHOOTINGSTAR': 'SHOOTING_STAR'
    }
    
    # Only rename if they exist
    existing_cols = set(df.columns)
    final_map = {k: v for k, v in rename_map.items() if k in existing_cols}
    df.rename(columns=final_map, inplace=True)
    
    # Fill NaN with 0 for patterns just in case
    for col in ['ENGULFING', 'HAMMER', 'SHOOTING_STAR']:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = df[col].fillna(0)

    # Ensure EMA_200 exists (sometimes named EMA_200)
    if 'EMA_200' not in df.columns and f'EMA_{config.EMA_PERIOD}' in df.columns:
         df['EMA_200'] = df[f'EMA_{config.EMA_PERIOD}']

    return df
