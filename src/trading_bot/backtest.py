import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta

# --- CONFIG ---
WATCHLIST = ["RELIANCE.NS", "TATASTEEL.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS"]
MEMORY_FILE = "trade_memory.csv"

def prepare_data(df):
    """Calculates indicators used in the bot."""
    df['EMA_200'] = df.ta.ema(length=200)
    df['RSI'] = df.ta.rsi(length=14)
    adx_df = df.ta.adx(length=14)
    if adx_df is not None:
        df['ADX'] = adx_df['ADX_14']
    df.dropna(inplace=True)
    return df

def run_backtest():
    print("Starting 30-Day Backtest Simulation...")
    all_trades = []

    for ticker in WATCHLIST:
        print(f"Analyzing history for {ticker}...")
        try:
            # Download 1 month of data
            df = yf.download(ticker, period="1mo", interval="15m", progress=False)
            if df.empty: continue
            
            # Clean data
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = prepare_data(df)

            # Simulate "If I bought at RSI < 30, did I win?"
            for i in range(len(df) - 5):
                row = df.iloc[i]
                future_price = df.iloc[i+5]['Close']
                current_price = row['Close']
                
                # LOGIC: Check if Buying Low (RSI < 30) worked
                if row['RSI'] < 30: 
                    result = 1 if future_price > current_price else 0
                    all_trades.append({
                        'rsi': row['RSI'],
                        'adx': row['ADX'],
                        'trend': 1 if row['Close'] > row['EMA_200'] else 0,
                        'result': result
                    })
                # LOGIC: Check if Selling High (RSI > 70) worked
                elif row['RSI'] > 70:
                    result = 1 if future_price < current_price else 0
                    all_trades.append({
                        'rsi': row['RSI'],
                        'adx': row['ADX'],
                        'trend': 1 if row['Close'] > row['EMA_200'] else 0,
                        'result': result
                    })

        except Exception as e:
            print(f"Error on {ticker}: {e}")

    # SAVE REAL DATA
    if len(all_trades) > 0:
        memory_df = pd.DataFrame(all_trades)
        memory_df.to_csv(MEMORY_FILE, index=False)
        print(f"BACKTEST COMPLETE. Generated {len(memory_df)} real historical scenarios.")
    else:
        print("No trades found.")

if __name__ == "__main__":
    run_backtest()