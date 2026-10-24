# config.py

# config.py

# config.py

WATCHLIST = ["RELIANCE.NS", "TATASTEEL.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS"]
TICKER = WATCHLIST[0] # Backwards compatibility default
TIMEFRAME = "5m"
LOOKBACK = 500  # Increased for indicators warmup
EMA_PERIOD = 200
STOP_LOSS_PCT = 0.01  # 1%

# Indicators
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
BB_LENGTH = 20
BB_STD = 2.0
SUPERTREND_LENGTH = 7
SUPERTREND_MULTIPLIER = 3.0
ADX_PERIOD = 14
ADX_THRESHOLD = 15 # Lowered for more trades
SCALPER_MODE = True # Ignore ADX filter if True
ATR_PERIOD = 14

# Titan System Settings
INITIAL_CAPITAL = 100000.0
RISK_PER_TRADE = 0.01  # 1%
MIN_RISK_REWARD = 1.5
MAX_DAILY_LOSSES = 2
LUNCH_START = "12:00"
LUNCH_END = "13:00"

# Apex System Settings
ML_CONFIDENCE_THRESHOLD = 0.75
MODEL_PATH = "apex_model.pkl"
FVG_THRESHOLD = 0.001 # 0.1% Minimum Gap size
