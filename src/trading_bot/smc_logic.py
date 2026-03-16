import pandas as pd
import numpy as np
from trading_bot import config

def detect_fvg(df):
    """
    Detects Bullish and Bearish Fair Value Gaps.
    Returns: DataFrame with added 'FVG_BULL' and 'FVG_BEAR' columns (boolean).
    Also returns a list of active zones {'top': float, 'bottom': float, 'type': str, 'created_at': datetime}
    """
    if len(df) < 3: return df, []
    
    # Vectorized FVG Detection
    # Bullish FVG: High of Candle 1 < Low of Candle 3
    # Gap is between High[i-2] and Low[i]
    
    high = df['High'].values
    low = df['Low'].values
    
    # Shifted arrays for comparison
    # i is Candle 3 (Current/Latest logic in vector)
    # i-1 is Candle 2 (Big impulse usually)
    # i-2 is Candle 1
    
    # We need to align indexes carefully. 
    # Pandas shift: shift(1) means "Previous value at current index".
    # So Low of Candle 3 is df['Low']. 
    # High of Candle 1 is df['High'].shift(2).
    
    high_shift2 = df['High'].shift(2)
    low_shift2 = df['Low'].shift(2)
    
    # Bullish FVG
    # Condition: Low > High_shift2 AND (Low - High_shift2) > Threshold
    # Ensure big gap
    fvg_bull_mask = (df['Low'] > high_shift2) & ((df['Low'] - high_shift2) > (df['Close'] * config.FVG_THRESHOLD))
    
    # Bearish FVG
    # Condition: High < Low_shift2
    fvg_bear_mask = (df['High'] < low_shift2) & ((low_shift2 - df['High']) > (df['Close'] * config.FVG_THRESHOLD))
    
    df['FVG_BULL'] = fvg_bull_mask
    df['FVG_BEAR'] = fvg_bear_mask
    
    # Extract Active Zones (Last 10 detected)
    active_zones = []
    
    # Extract Active Zones (Last 10 detected)
    active_zones = []
    
    # Re-extract cleanly list logic:
    # Just use the mask indices
    bull_indices = df[df['FVG_BULL']].index
    for idx in bull_indices[-5:]: # Last 5
        # Need value from 2 candles ago.
        loc_idx = df.index.get_loc(idx)
        val_bottom = df.iloc[loc_idx-2]['High']
        val_top = df.loc[idx, 'Low']
        active_zones.append({'type': 'FVG_BULL', 'top': val_top, 'bottom': val_bottom, 'created_at': idx})

    bear_indices = df[df['FVG_BEAR']].index
    for idx in bear_indices[-5:]:
        loc_idx = df.index.get_loc(idx)
        val_top = df.iloc[loc_idx-2]['Low']
        val_bottom = df.loc[idx, 'High'] # Gap is below this high? No.
        # Bear FVG: Candle 1 Low (Top of gap) -> Candle 3 High (Bottom of gap).
        # Gap is between Low[i-2] and High[i].
        active_zones.append({'type': 'FVG_BEAR', 'top': val_top, 'bottom': val_bottom, 'created_at': idx})
        
    return df, active_zones

def detect_liquidity_sweeps(df, lookback=20):
    """
    Detects if the current candle 'swept' a recent Swing Low/High but closed back inside.
    """
    # Swing Low: Lowest point in Window.
    # We check if Low[i] < Min(Low[i-1...i-lookback]) AND Close[i] > Min(...)
    
    recent_lows = df['Low'].rolling(window=lookback).min().shift(1) # Min of previous period
    recent_highs = df['High'].rolling(window=lookback).max().shift(1)
    
    sweep_bull = (df['Low'] < recent_lows) & (df['Close'] > recent_lows) # Wick below, Body above
    sweep_bear = (df['High'] > recent_highs) & (df['Close'] < recent_highs) # Wick above, Body below
    
    df['SWEEP_BULL'] = sweep_bull
    df['SWEEP_BEAR'] = sweep_bear
    
    return df
