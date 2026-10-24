
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(os.getcwd()) / "src"))

try:
    import pandas as pd
    import numpy as np
    import yfinance as yf
    print("✅ Basic libraries imported")
except ImportError as e:
    print(f"❌ Basic library missing: {e}")

try:
    import pandas_ta_classic
    print("✅ pandas_ta_classic imported")
except ImportError:
    print("❌ pandas_ta_classic missing")

try:
    import pandas_ta
    print("✅ pandas_ta imported")
except ImportError:
    print("❌ pandas_ta missing")

try:
    from trading_bot import config
    from trading_bot import market_analyzer
    from trading_bot import pattern_recognition
    print("✅ Local modules imported")
except Exception as e:
    print(f"❌ Local module import failed: {e}")
    import traceback
    traceback.print_exc()
