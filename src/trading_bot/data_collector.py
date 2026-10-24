"""
Data Collector for Training - Gathers Historical Market Data with Labels

This script collects 2+ years of historical data for Indian stocks (NSE)
and labels each setup as WIN/LOSS based on actual price movement.

Features collected:
- Technical indicators (EMA, RSI, ADX, ATR, Supertrend, VWAP)
- SMC patterns (FVG, liquidity sweeps)
- Volume analysis
- Sentiment scores
- Market regime detection

Requirements:
- yfinance for market data
- pandas, numpy for processing
- Minimum 1000 labeled samples per stock
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
WATCHLIST = [
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 
    'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'LT.NS',
    'HINDUNILVR.NS', 'ITC.NS'
]

TRAINING_DATA_FILE = 'training_data.csv'
YEARS_OF_DATA = 2
MIN_SAMPLES_PER_STOCK = 1000

class DataCollector:
    def __init__(self):
        self.watchlist = WATCHLIST
        self.training_data = []
        
    def fetch_historical_data(self, ticker: str, period: str = "2y") -> pd.DataFrame:
        """Fetch historical data for a ticker"""
        try:
            logger.info(f"Fetching data for {ticker}...")
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval="1d")
            
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                return pd.DataFrame()
                
            df.reset_index(inplace=True)
            df['Ticker'] = ticker
            logger.info(f"✓ Fetched {len(df)} records for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        if df.empty:
            return df
            
        # EMA calculations
        df['EMA_9'] = df['Close'].ewm(span=9).mean()
        df['EMA_21'] = df['Close'].ewm(span=21).mean()
        df['EMA_50'] = df['Close'].ewm(span=50).mean()
        df['EMA_200'] = df['Close'].ewm(span=200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # ADX calculation
        df = self._calculate_adx(df)
        
        # ATR
        df['TR'] = df[['High', 'Low']].max(axis=1) - df[['High', 'Low']].min(axis=1)
        df['TR'] = df['TR'].combine(df['High'] - df['Close'].shift(), max)
        df['TR'] = df['TR'].combine(df['Close'].shift() - df['Low'], max)
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        # Supertrend
        df = self._calculate_supertrend(df)
        
        # VWAP
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        # Volume analysis
        df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Spike'] = (df['Volume'] > df['Volume_SMA'] * 1.5).astype(int)
        
        return df

    def _calculate_adx(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate ADX (Average Directional Index)"""
        # Calculate True Range
        df['TR'] = df['High'] - df['Low']
        df['TR'] = df['TR'].combine(df['High'] - df['Close'].shift(), max)
        df['TR'] = df['TR'].combine(df['Close'].shift() - df['Low'], max)
        
        # Calculate +DM and -DM
        df['+DM'] = np.where(
            (df['High'] - df['High'].shift()) > (df['Low'].shift() - df['Low']),
            np.maximum(df['High'] - df['High'].shift(), 0),
            0
        )
        df['-DM'] = np.where(
            (df['Low'].shift() - df['Low']) > (df['High'] - df['High'].shift()),
            np.maximum(df['Low'].shift() - df['Low'], 0),
            0
        )
        
        # Smooth TR, +DM, -DM
        df['TR_14'] = df['TR'].rolling(window=14).mean()
        df['+DM_14'] = df['+DM'].rolling(window=14).mean()
        df['-DM_14'] = df['-DM'].rolling(window=14).mean()
        
        # Calculate +DI and -DI
        df['+DI'] = 100 * (df['+DM_14'] / df['TR_14'])
        df['-DI'] = 100 * (df['-DM_14'] / df['TR_14'])
        
        # Calculate ADX
        df['DX'] = 100 * (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI']))
        df['ADX'] = df['DX'].rolling(window=14).mean()
        
        return df

    def _calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Supertrend indicator"""
        multiplier = 3
        atr_period = 10
        
        # Calculate ATR
        df['TR'] = df['High'] - df['Low']
        df['TR'] = df['TR'].combine(df['High'] - df['Close'].shift(), max)
        df['TR'] = df['TR'].combine(df['Close'].shift() - df['Low'], max)
        df['ATR_ST'] = df['TR'].rolling(window=atr_period).mean()
        
        # Calculate basic upper and lower bands
        df['Basic_UB'] = (df['High'] + df['Low']) / 2 + (multiplier * df['ATR_ST'])
        df['Basic_LB'] = (df['High'] + df['Low']) / 2 - (multiplier * df['ATR_ST'])
        
        # Calculate final upper and lower bands
        df['Final_UB'] = 0.0
        df['Final_LB'] = 0.0
        
        for i in range(atr_period, len(df)):
            if df['Basic_UB'].iloc[i] < df['Final_UB'].iloc[i-1] or df['Close'].iloc[i-1] > df['Final_UB'].iloc[i-1]:
                df.loc[df.index[i], 'Final_UB'] = df['Basic_UB'].iloc[i]
            else:
                df.loc[df.index[i], 'Final_UB'] = df['Final_UB'].iloc[i-1]
                
            if df['Basic_LB'].iloc[i] > df['Final_LB'].iloc[i-1] or df['Close'].iloc[i-1] < df['Final_LB'].iloc[i-1]:
                df.loc[df.index[i], 'Final_LB'] = df['Basic_LB'].iloc[i]
            else:
                df.loc[df.index[i], 'Final_LB'] = df['Final_LB'].iloc[i-1]
        
        # Calculate Supertrend
        df['Supertrend'] = 0.0
        for i in range(atr_period, len(df)):
            if df['Supertrend'].iloc[i-1] == df['Final_UB'].iloc[i-1] and df['Close'].iloc[i] <= df['Final_UB'].iloc[i]:
                df.loc[df.index[i], 'Supertrend'] = df['Final_UB'].iloc[i]
            elif df['Supertrend'].iloc[i-1] == df['Final_UB'].iloc[i-1] and df['Close'].iloc[i] > df['Final_UB'].iloc[i]:
                df.loc[df.index[i], 'Supertrend'] = df['Final_LB'].iloc[i]
            elif df['Supertrend'].iloc[i-1] == df['Final_LB'].iloc[i-1] and df['Close'].iloc[i] >= df['Final_LB'].iloc[i]:
                df.loc[df.index[i], 'Supertrend'] = df['Final_LB'].iloc[i]
            elif df['Supertrend'].iloc[i-1] == df['Final_LB'].iloc[i-1] and df['Close'].iloc[i] < df['Final_LB'].iloc[i]:
                df.loc[df.index[i], 'Supertrend'] = df['Final_UB'].iloc[i]
        
        return df

    def detect_smc_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect Smart Money Concepts patterns"""
        # Fair Value Gap (FVG) detection
        df['FVG_Bullish'] = 0
        df['FVG_Bearish'] = 0
        
        for i in range(2, len(df)):
            # Bullish FVG: High of candle 2 gaps below Low of candle 0
            if df['High'].iloc[i-2] < df['Low'].iloc[i]:
                df.loc[df.index[i], 'FVG_Bullish'] = 1
                
            # Bearish FVG: Low of candle 2 gaps above High of candle 0
            if df['Low'].iloc[i-2] > df['High'].iloc[i]:
                df.loc[df.index[i], 'FVG_Bearish'] = 1
        
        # Liquidity sweep detection
        df['Liquidity_Sweep'] = 0
        lookback = 20
        
        for i in range(lookback, len(df)):
            recent_high = df['High'].iloc[i-lookback:i].max()
            recent_low = df['Low'].iloc[i-lookback:i].min()
            
            # Bullish sweep: price breaks above recent high then pulls back
            if df['High'].iloc[i] > recent_high and df['Close'].iloc[i] < recent_high:
                df.loc[df.index[i], 'Liquidity_Sweep'] = 1  # Bullish sweep
                
            # Bearish sweep: price breaks below recent low then pulls back
            elif df['Low'].iloc[i] < recent_low and df['Close'].iloc[i] > recent_low:
                df.loc[df.index[i], 'Liquidity_Sweep'] = -1  # Bearish sweep
        
        return df

    def detect_market_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect market regime (Bull/Bear/Sideways)"""
        # Simple regime detection based on 200 EMA
        df['Market_Regime'] = np.where(
            df['Close'] > df['EMA_200'], 
            1,  # Bullish
            np.where(df['Close'] < df['EMA_200'], -1, 0)  # Bearish or Sideways
        )
        
        # Volatility regime based on ATR percentile
        df['ATR_Percentile'] = df['ATR'].rolling(window=252).rank(pct=True)
        df['Volatility_Regime'] = np.where(
            df['ATR_Percentile'] > 0.7, 2,  # High volatility
            np.where(df['ATR_Percentile'] < 0.3, 0, 1)  # Low or Normal volatility
        )
        
        return df

    def label_outcomes(self, df: pd.DataFrame, lookforward: int = 10) -> pd.DataFrame:
        """Label each setup as WIN/LOSS based on future price movement"""
        df['Outcome'] = 'UNKNOWN'
        df['Target_Hit'] = 0
        df['Stop_Hit'] = 0
        df['Holding_Period'] = 0
        
        for i in range(len(df) - lookforward):
            entry_price = df['Close'].iloc[i]
            
            # Define target (2R) and stop loss (1R) based on ATR
            atr = df['ATR'].iloc[i] if not pd.isna(df['ATR'].iloc[i]) else entry_price * 0.01
            target_price = entry_price + (2 * atr)  # 2R target
            stop_price = entry_price - (1 * atr)    # 1R stop
            
            # Look for target or stop hit within lookforward period
            future_prices = df['High'].iloc[i:i+lookforward+1]
            future_lows = df['Low'].iloc[i:i+lookforward+1]
            
            target_hit_idx = (future_prices >= target_price).idxmax() if (future_prices >= target_price).any() else None
            stop_hit_idx = (future_lows <= stop_price).idxmax() if (future_lows <= stop_price).any() else None
            
            # Determine outcome
            if target_hit_idx is not None and (stop_hit_idx is None or target_hit_idx <= stop_hit_idx):
                df.loc[df.index[i], 'Outcome'] = 'WIN'
                df.loc[df.index[i], 'Target_Hit'] = 1
                df.loc[df.index[i], 'Holding_Period'] = target_hit_idx - i
            elif stop_hit_idx is not None:
                df.loc[df.index[i], 'Outcome'] = 'LOSS'
                df.loc[df.index[i], 'Stop_Hit'] = 1
                df.loc[df.index[i], 'Holding_Period'] = stop_hit_idx - i
            else:
                # If neither hit, check if price moved favorably by 2%
                final_price = df['Close'].iloc[i+lookforward] if i+lookforward < len(df) else entry_price
                if (final_price - entry_price) / entry_price >= 0.02:  # 2% move
                    df.loc[df.index[i], 'Outcome'] = 'WIN'
                else:
                    df.loc[df.index[i], 'Outcome'] = 'LOSS'
        
        return df

    def detect_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect potential buy/sell signals based on technical setup"""
        df['Signal_Type'] = 'NONE'
        
        for i in range(200, len(df)):  # Need enough data for indicators
            # Bullish setup conditions
            bullish_setup = (
                df['Close'].iloc[i] > df['EMA_21'].iloc[i] and  # Price above EMA21
                df['EMA_9'].iloc[i] > df['EMA_21'].iloc[i] and   # EMA9 above EMA21
                df['RSI'].iloc[i] < 60 and                       # RSI not overbought
                df['ADX'].iloc[i] > 25 and                       # Strong trend
                df['Close'].iloc[i] > df['Supertrend'].iloc[i]   # Above Supertrend
            )
            
            # Bearish setup conditions
            bearish_setup = (
                df['Close'].iloc[i] < df['EMA_21'].iloc[i] and  # Price below EMA21
                df['EMA_9'].iloc[i] < df['EMA_21'].iloc[i] and   # EMA9 below EMA21
                df['RSI'].iloc[i] > 40 and                       # RSI not oversold
                df['ADX'].iloc[i] > 25 and                       # Strong trend
                df['Close'].iloc[i] < df['Supertrend'].iloc[i]   # Below Supertrend
            )
            
            if bullish_setup:
                df.loc[df.index[i], 'Signal_Type'] = 'BUY'
            elif bearish_setup:
                df.loc[df.index[i], 'Signal_Type'] = 'SELL'
        
        return df

    def collect_stock_data(self, ticker: str) -> List[Dict]:
        """Collect and process data for one stock"""
        logger.info(f"=== Processing {ticker} ===")
        
        # Fetch data
        df = self.fetch_historical_data(ticker, f"{YEARS_OF_DATA}y")
        if df.empty or len(df) < 200:
            logger.warning(f"Insufficient data for {ticker}")
            return []
        
        # Calculate all indicators
        df = self.calculate_indicators(df)
        df = self.detect_smc_patterns(df)
        df = self.detect_market_regime(df)
        df = self.detect_signals(df)
        df = self.label_outcomes(df)
        
        # Extract training samples
        samples = []
        for i in range(200, len(df)):  # Skip first 200 rows for indicator warmup
            if df['Signal_Type'].iloc[i] != 'NONE' and df['Outcome'].iloc[i] != 'UNKNOWN':
                sample = {
                    'ticker': ticker.replace('.NS', ''),
                    'timestamp': df['Date'].iloc[i].strftime('%Y-%m-%d'),
                    'open': df['Open'].iloc[i],
                    'high': df['High'].iloc[i],
                    'low': df['Low'].iloc[i],
                    'close': df['Close'].iloc[i],
                    'volume': df['Volume'].iloc[i],
                    'ema_9': df['EMA_9'].iloc[i],
                    'ema_21': df['EMA_21'].iloc[i],
                    'ema_50': df['EMA_50'].iloc[i],
                    'ema_200': df['EMA_200'].iloc[i],
                    'rsi': df['RSI'].iloc[i],
                    'adx': df['ADX'].iloc[i],
                    'atr': df['ATR'].iloc[i],
                    'supertrend': df['Supertrend'].iloc[i],
                    'vwap': df['VWAP'].iloc[i],
                    'fvg_bullish': df['FVG_Bullish'].iloc[i],
                    'fvg_bearish': df['FVG_Bearish'].iloc[i],
                    'liquidity_sweep': df['Liquidity_Sweep'].iloc[i],
                    'volume_spike': df['Volume_Spike'].iloc[i],
                    'market_regime': df['Market_Regime'].iloc[i],
                    'volatility_regime': df['Volatility_Regime'].iloc[i],
                    'signal_type': df['Signal_Type'].iloc[i],
                    'outcome': df['Outcome'].iloc[i],
                    'target_hit': df['Target_Hit'].iloc[i],
                    'stop_hit': df['Stop_Hit'].iloc[i],
                    'holding_period': df['Holding_Period'].iloc[i]
                }
                samples.append(sample)
        
        logger.info(f"✓ Collected {len(samples)} labeled samples for {ticker}")
        return samples

    def run_collection(self):
        """Run the complete data collection process"""
        logger.info("[START] Starting Data Collection Process")
        logger.info(f"Target: {MIN_SAMPLES_PER_STOCK} samples per stock")
        logger.info(f"Watchlist: {self.watchlist}")
        
        all_samples = []
        
        for ticker in self.watchlist:
            samples = self.collect_stock_data(ticker)
            all_samples.extend(samples)
            
            # Progress check
            ticker_samples = [s for s in all_samples if s['ticker'] == ticker.replace('.NS', '')]
            logger.info(f"Progress: {ticker} - {len(ticker_samples)} samples")
            
            if len(ticker_samples) >= MIN_SAMPLES_PER_STOCK:
                logger.info(f"[OK] {ticker} target reached!")
        
        # Save to CSV
        if all_samples:
            df = pd.DataFrame(all_samples)
            df.to_csv(TRAINING_DATA_FILE, index=False)
            logger.info(f"[OK] Training data saved to {TRAINING_DATA_FILE}")
            logger.info(f"[STATS] Total samples collected: {len(df)}")
            logger.info(f"[^] Win rate: {(df['outcome'] == 'WIN').mean():.2%}")
            
            # Summary by stock
            summary = df.groupby('ticker').agg({
                'outcome': ['count', lambda x: (x == 'WIN').mean()]
            }).round(3)
            logger.info(f"\n📋 Sample distribution by stock:")
            logger.info(summary)
        else:
            logger.error("[X] No data collected!")

if __name__ == "__main__":
    collector = DataCollector()
    collector.run_collection()
