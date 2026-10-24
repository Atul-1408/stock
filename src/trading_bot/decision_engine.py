import pandas as pd
from trading_bot import config
from trading_bot import smc_logic
from trading_bot import market_analyzer
from trading_bot.ai_validator import AIValidator

# Initialize AI Lazily
ai = None

def analyze_setup(df):
    """
    Analyzes the latest candle for trading setups using Titan + Apex (SMC/AI) rules.
    """
    global ai
    if ai is None:
        ai = AIValidator()

    if df is None or len(df) < 1:
        return {'signal': 'WAIT', 'message': 'Insufficient Data'}
    
    # 1. SMC Processing
    df, active_fvgs = smc_logic.detect_fvg(df)
    df = smc_logic.detect_liquidity_sweeps(df)
    
    row = df.iloc[-1]
    
    # Construct Column Names based on Config
    rsi_col = f"RSI_{config.RSI_PERIOD}"
    bbl_col = f"BBL_{config.BB_LENGTH}_{config.BB_STD}"
    bbu_col = f"BBU_{config.BB_LENGTH}_{config.BB_STD}"
    ema_col = f"EMA_{config.EMA_PERIOD}"
    vwap_col = "VWAP_D"
    adx_col = f"ADX_{config.ADX_PERIOD}"
    atr_col = f"ATR_{config.ATR_PERIOD}"
    
    # Check if columns exist
    for col in [rsi_col, bbl_col, ema_col, vwap_col, adx_col, atr_col]:
        if col not in df.columns:
            return {'signal': 'WAIT', 'message': f'Missing Indicator: {col}'}
            
    # Extract Values
    close_price = row['Close']
    open_price = row['Open']
    low_price = row['Low']
    bbl = row[bbl_col]
    bbu = row[bbu_col]
    ema = row[ema_col]
    vwap = row[vwap_col]
    adx = row[adx_col]
    atr = row[atr_col]
    rsi = row[rsi_col]
    
    # Patterns (CDL_...)
    is_hammer = row.get('CDL_HAMMER', 0) != 0
    is_engulfing_bull = row.get('CDL_ENGULFING', 0) > 0 
    
    # SMC Patterns
    is_sweep_bull = row.get('SWEEP_BULL', False)
    
    confidence = ai.get_confidence(row)
    trend_val = 1 if close_price > ema else 0 # 1 for Bullish, 0 for Bearish
    
    signal_data = {
        'signal': 'WAIT',
        'strategy': None,
        'stop_loss': 0.0,
        'take_profit': 0.0,
        'atr': atr,
        'confidence': confidence,
        'rsi': rsi,
        'adx': adx,
        'trend': trend_val,
        'message': f"P: {close_price:.2f} | ADX: {adx:.1f} | ML: {confidence:.2f}"
    }
    
    # AI Score Check Helper
    def check_ai_confidence(base_msg):
        confidence = ai.get_confidence(row)
        if confidence < config.ML_CONFIDENCE_THRESHOLD:
            signal_data['message'] = f"Filtered by AI: Conf {confidence:.2f} < {config.ML_CONFIDENCE_THRESHOLD} ({base_msg})"
            signal_data['signal'] = 'WAIT' # Overwrite to Wait
            return False
        return True

    # --- News Filter Placeholder ---
    # TODO: Integration with NewsAPI or similar.
    # if news_sentiment < -0.5:
    #     signal_data['message'] = "Filtered: Negative News Sentiment"
    #     return signal_data

    # Filter 1: ADX (Trend Strength / Volatility Quality)
    # If SCALPER_MODE is True, we skip this check (Assume user wants action)
    if not config.SCALPER_MODE:
        if adx < config.ADX_THRESHOLD:
             # Exception: Liquidity Sweeps work well in range/choppy (Low ADX)
             if not is_sweep_bull:
                signal_data['message'] = f"Filtered: ADX Too Low ({adx:.1f})"
                return signal_data

    # --- Strategy A: SMC Liquidity Sweep (Reversal) ---
    if is_sweep_bull:
        if check_ai_confidence("Liquidity Sweep"):
            signal_data['signal'] = 'STRONG BUY'
            signal_data['strategy'] = 'SMC Liquidity Sweep'
            
            # Precise ATR Levels
            # SL = CMP - 2*ATR
            # TGT = CMP + 4*ATR
            signal_data['stop_loss'] = close_price - (2 * atr)
            signal_data['take_profit'] = close_price + (4 * atr)
            
            signal_data['message'] = "Liquidity Sweep Detected + AI Confirmed"
            return signal_data

    # --- Strategy B: FVG Retest (Trend) ---
    for fvg in active_fvgs:
        if fvg['type'] == 'FVG_BULL':
            if (low_price <= fvg['top']) and (low_price >= fvg['bottom']):
                if is_hammer or is_engulfing_bull:
                    if check_ai_confidence("FVG Retest"):
                        signal_data['signal'] = 'STRONG BUY'
                        signal_data['strategy'] = 'SMC FVG Retest'
                        
                        # Precise ATR Levels (Override SMC logic for consistency if requested, 
                        # or use Hybrid: max(SMC_SL, ATR_SL)? User asked for Exact formula.)
                        signal_data['stop_loss'] = close_price - (2 * atr) 
                        signal_data['take_profit'] = close_price + (4 * atr)
                        
                        signal_data['message'] = "FVG Retest + AI Confirmed"
                        return signal_data
    
    # --- Strategy C: Trend Rider (Classic Titan) ---
    is_above_vwap = close_price > vwap
    if is_above_vwap and (close_price > ema) and is_engulfing_bull:
        if check_ai_confidence("Trend Rider"):
            signal_data['signal'] = 'CONTINUATION BUY'
            signal_data['strategy'] = 'Trend Rider (Apex)'
            
            # Precise ATR Levels
            signal_data['stop_loss'] = close_price - (2 * atr)
            signal_data['take_profit'] = close_price + (4 * atr)
            
            signal_data['message'] = "Trend Continuation + AI Confirmed"
            return signal_data
            
    # --- Strategy D: Pivot Breakout / Pullback (New) ---
    # Fetch Pivots
    pivots = market_analyzer.get_daily_pivots(config.TICKER)
    if pivots:
        P, R1, S1 = pivots['P'], pivots['R1'], pivots['S1']
        
        # 1. Breakout Buy (Above Resistance)
        if (close_price > R1) and (open_price < R1): # Crossing R1
             if check_ai_confidence("Breakout Buy"):
                signal_data['signal'] = 'BREAKOUT BUY'
                signal_data['strategy'] = 'Resistance Breakout'
                signal_data['stop_loss'] = R1 - (atr) # Stop just below breakout point
                signal_data['take_profit'] = close_price + (4 * atr)
                signal_data['message'] = f"Price broke above R1 ({R1:.2f})"
                return signal_data

        # 2. Pullback Buy (Bounce off Support)
        # Low touched S1, but Close is Green (Hammer or just Green)
        if (low_price <= S1) and (close_price > open_price) and (close_price > S1):
             if check_ai_confidence("Pullback Buy"):
                signal_data['signal'] = 'PULLBACK BUY'
                signal_data['strategy'] = 'Support Bounce'
                signal_data['stop_loss'] = low_price - (atr * 0.5)
                signal_data['take_profit'] = P # Target back to Pivot
                signal_data['message'] = f"Bounce off Support S1 ({S1:.2f})"
                return signal_data

    return signal_data
