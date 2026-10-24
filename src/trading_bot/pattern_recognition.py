import pandas as pd
import pandas_ta_classic as ta
from trading_bot import config
import numpy as np

# --- Pure Python Pattern Logic ---
# Replacing TA-Lib dependency with manual calculation

class PatternRecognizer:
    @staticmethod
    def calculate_indicators(df):
        """
        Calculates standard indicators (RSI, EMA, etc.)
        """
        if df is None: return df
        
        # 1. EMA 200
        df.ta.ema(length=config.EMA_PERIOD, append=True)
        # 2. RSI
        df.ta.rsi(length=config.RSI_PERIOD, append=True)
        # 3. Bollinger Bands
        df.ta.bbands(length=config.BB_LENGTH, std=config.BB_STD, append=True)
        # 4. Supertrend
        df.ta.supertrend(length=config.SUPERTREND_LENGTH, multiplier=config.SUPERTREND_MULTIPLIER, append=True)
        # 5. ADX
        adx_df = df.ta.adx(length=config.ADX_PERIOD)
        if adx_df is not None: df = pd.concat([df, adx_df], axis=1)
        # 6. ATR
        atr_series = df.ta.atr(length=config.ATR_PERIOD)
        if atr_series is not None:
             if isinstance(atr_series, pd.Series): atr_series.name = f"ATR_{config.ATR_PERIOD}"
             df = pd.concat([df, atr_series], axis=1)
        # 7. VWAP
        if 'Volume' in df.columns: df.ta.vwap(append=True)
        
        return df

    @staticmethod
    def detect_patterns(df):
        """
        Manually detects patterns without TA-Lib.
        Output Columns: 'CDL_ENGULFING', 'CDL_HAMMER', 'CDL_DOJI'
        Values: 100 (Bullish), -100 (Bearish), 0 (None)
        """
        # Pre-calculate basic properties
        O = df['Open']
        H = df['High']
        L = df['Low']
        C = df['Close']
        
        Body = abs(C - O)
        Body_Top = np.maximum(C, O)
        Body_Bottom = np.minimum(C, O)
        Upper_Wick = H - Body_Top
        Lower_Wick = Body_Bottom - L
        Total_Range = H - L
        
        # Initialize Columns
        df['CDL_ENGULFING'] = 0
        df['CDL_HAMMER'] = 0
        df['CDL_DOJI'] = 0
        
        # --- 1. Bullish Engulfing ---
        # Rule:
        # 1. Previous Candle Red (Prev_Close < Prev_Open)
        # 2. Current Candle Green (Curr_Close > Curr_Open)
        # 3. Curr_Open < Prev_Close (Gap Down or equal) - strict definition varies, often simplified to Body covers Body
        # 4. Curr_Close > Prev_Open (Engulfs previous open)
        # Simplified: Current Green Body completely engulfs Previous Red Body.
        
        prev_O = O.shift(1)
        prev_C = C.shift(1)
        
        is_prev_red = prev_C < prev_O
        is_curr_green = C > O
        engulfs = (C > prev_O) & (O < prev_C) # Strictly covering the body
        
        bull_engulfing_mask = is_prev_red & is_curr_green & engulfs
        df.loc[bull_engulfing_mask, 'CDL_ENGULFING'] = 100
        
        # --- 2. Hammer ---
        # Rule:
        # 1. Small Body (Optional: Body < 30% of range? Standard: 2x lower wick)
        # 2. Long Lower Wick (Lower Wick > 2 * Body)
        # 3. Small Upper Wick (Upper Wick < Body or negligible)
        
        long_lower_wick = Lower_Wick > (2 * Body)
        small_upper_wick = Upper_Wick < (0.5 * Body) # Strict
        # Context usually requires downtrend, but we define pattern geometry here.
        
        hammer_mask = long_lower_wick & small_upper_wick
        df.loc[hammer_mask, 'CDL_HAMMER'] = 100
        
        # --- 3. Doji ---
        # Rule: Body is very small relative to range.
        # e.g., Body < 10% of Total Range
        
        doji_mask = Body <= (0.1 * Total_Range)
        df.loc[doji_mask, 'CDL_DOJI'] = 100
        
        return df

# Helper wrapper for compatibility
def detect_all(df):
    df = PatternRecognizer.calculate_indicators(df)
    df = PatternRecognizer.detect_patterns(df)
    return df
