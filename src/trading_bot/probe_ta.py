import pandas as pd
import pandas_ta_classic as ta

def probe():
    df = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [105, 106, 107, 108, 109],
        'Low': [95, 96, 97, 98, 99],
        'Close': [102, 103, 104, 105, 106],
        'Volume': [1000, 1000, 1000, 1000, 1000]
    })
    
    print("Testing EMA...")
    try:
        # Try Accessor
        # Note: pandas_ta requires DataFrame to have datetime index usually? No.
        res = df.ta.ema(length=2)
        print("df.ta.ema works:", res is not None)
    except Exception as e:
        print("df.ta.ema failed:", e)

    print("Testing Patterns...")
    try:
        # Try cdl_engulfing via accessor?
        # df.ta.cdl_engulfing usually doesn't exist directly.
        # df.ta.cdl_pattern(name="engulfing")
        res = df.ta.cdl_pattern(name="engulfing")
        print("df.ta.cdl_pattern works:", res is not None)
        print("Columns:", res.columns)
    except Exception as e:
        print("df.ta.cdl_pattern failed:", e)
        
    try:
        # Try top level logic if accessor failed
        import pandas_ta_classic as ta_module
        res = ta_module.ema(df['Close'], length=2)
        print("ta_module.ema works:", res is not None)
    except Exception as e:
        print("ta_module.ema failed:", e)

if __name__ == "__main__":
    probe()
