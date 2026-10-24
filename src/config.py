"""Application configuration settings.

This file centralizes app-wide settings so your API keys and constants
are managed in one place.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load values from .env file (if present)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Main configuration class for the project."""

    BASE_DIR = BASE_DIR

    # Environment mode
    ENVIRONMENT = os.getenv("FLASK_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    IS_PRODUCTION = ENVIRONMENT == "production"

    # JWT Configuration
    _raw_jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if _raw_jwt_secret:
        JWT_SECRET_KEY = _raw_jwt_secret
    elif IS_PRODUCTION:
        raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET_KEY must be set in production environment.")
    else:
        import secrets
        JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))

    JWT_ACCESS_TOKEN_EXPIRES_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_DAYS", "7"))

    # CORS Allowed Origins
    _default_cors = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ]
    _env_cors = os.getenv("CORS_ALLOWED_ORIGINS", "")
    CORS_ALLOWED_ORIGINS = [orig.strip() for orig in _env_cors.split(",") if orig.strip()] if _env_cors else _default_cors

    # Rate Limiting Storage URI
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # NewsAPI key should be set in .env as: NEWS_API_KEY=your_key_here
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

    # Finnhub API key
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

    # Telegram Bot
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # Gmail SMTP (for OTP emails)
    GMAIL_SENDER = os.getenv("GMAIL_SENDER", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

    # Gemini AI Key
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Trading Safety Controls
    # Defaults strictly to PAPER. Live trading requires TRADING_MODE=LIVE and ALLOW_LIVE_TRADING=true.
    TRADING_MODE = os.getenv("TRADING_MODE", "PAPER").upper()
    ALLOW_LIVE_TRADING = os.getenv("ALLOW_LIVE_TRADING", "false").lower() in ("true", "1", "yes")

    if TRADING_MODE == "LIVE" and not ALLOW_LIVE_TRADING:
        raise RuntimeError(
            "CRITICAL SAFETY ERROR: TRADING_MODE is set to 'LIVE' but ALLOW_LIVE_TRADING is false. "
            "Live trading requires explicit dual authorization via ALLOW_LIVE_TRADING=true."
        )

    IS_LIVE_TRADING_ENABLED = (TRADING_MODE == "LIVE" and ALLOW_LIVE_TRADING)

    # SQLite database file path (supports container/persistent storage mounts via DATABASE_PATH or DB_PATH)
    _db_path_env = os.getenv("DATABASE_PATH", os.getenv("DB_PATH", "")).strip()
    DB_PATH = Path(_db_path_env) if _db_path_env else (BASE_DIR / "data" / "stock_dashboard.db")

    @classmethod
    def validate_production_config(cls):
        """Validate production configuration before service launch."""
        errors = []
        warnings = []

        if cls.IS_PRODUCTION:
            if not cls.JWT_SECRET_KEY or len(cls.JWT_SECRET_KEY) < 32:
                errors.append("JWT_SECRET_KEY must be at least 32 characters in production.")

            if "*" in cls.CORS_ALLOWED_ORIGINS:
                errors.append("Wildcard '*' in CORS_ALLOWED_ORIGINS is prohibited in production.")

            if cls.IS_LIVE_TRADING_ENABLED:
                warnings.append("LIVE TRADING IS ENABLED. Verify risk limits and brokerage credentials.")
            else:
                # Confirm paper trading
                pass

            if cls.RATELIMIT_STORAGE_URI == "memory://":
                warnings.append(
                    "RATELIMIT_STORAGE_URI is 'memory://'. Consider using Redis ('redis://...') in multi-worker production."
                )

        if errors:
            raise RuntimeError(f"PRODUCTION CONFIGURATION VALIDATION FAILED: {'; '.join(errors)}")

        return {"valid": True, "warnings": warnings}

    # Fetch settings
    NEWS_PAGE_SIZE = 20
    PRICE_LOOKBACK_DAYS = 30
    NEWS_LANGUAGE = "en"

    # Sentiment model settings
    FINBERT_MODEL_NAME = "ProsusAI/finbert"
    DEFAULT_SENTIMENT_MODEL = "finbert"

    # Default Tickers for Coverage
    # USA: Nasdaq/NYSE
    # INDIA: NSE (.NS suffix)
    # Multi-Stock Support
    DEFAULT_TICKERS = [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "LLY",
        "JPM", "XOM", "V", "JNJ", "MA", "PG", "AVGO", "HD", "CVX", "MRK",
        "ABBV", "COST", "PEP", "ADBE", "KO", "WMT", "BAC", "CRM", "TMO", "MCD",
        "ACN", "ABT", "CSCO", "PFE", "DHR", "INTU", "LIN", "NFLX", "VZ", "INTC",
        "AMD", "CMCSA", "QCOM", "DIS", "TXN", "AMGN", "NEE", "PM", "IBM", "HON",
        "RTX", "AXP", "SPGI", "CAT", "GS", "LOW", "DE", "SYK", "BLK", "MS",
        "BA", "ELV", "SBUX", "PLD", "UPS", "AMAT", "ISRG", "ADP", "LMT", "GILD",
        "PDD", "MDLZ", "T", "ADI", "TJX", "MMC", "CVS", "GE", "SCHW", "LRCX",
        "REGN", "PGR", "ZTS", "CI", "VRTX", "BKNG", "CB", "HUM", "MU", "PANW",
        "SNPS", "EOG", "SLB", "BSX", "ITW", "MO", "HCA", "C", "ORCL", "CDNS",
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LICI.NS", "HINDUNILVR.NS",
        "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS", "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS", "TATAMOTORS.NS",
        "NTPC.NS", "AXISBANK.NS", "ADANIPORTS.NS", "COALINDIA.NS", "ADANIGREEN.NS", "ASIANPAINT.NS", "BAJAJFINSV.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "M&M.NS",
        "POWERGRID.NS", "SBILIFE.NS", "VBL.NS", "IRFC.NS", "SIEMENS.NS", "ADANIPOWER.NS", "HAL.NS", "INDIGO.NS", "BPCL.NS", "DLF.NS",
        "CHOLAFIN.NS", "GRASIM.NS", "BRITANNIA.NS", "TRENT.NS", "ZOMATO.NS", "BEL.NS", "HINDALCO.NS", "NESTLEIND.NS", "TATACONSUM.NS", "GAIL.NS",
        "JIODFSL.NS", "SHREECEM.NS", "ADANITRANS.NS", "CIPLA.NS", "SBICARD.NS", "DRREDDY.NS", "HDFCLIFE.NS", "APOLLOHOSP.NS", "TECHM.NS", "EICHERMOT.NS",
        "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "DIVISLAB.NS", "HINDZINC.NS", "PIDILITIND.NS", "TVSMOTOR.NS", "JINDALSTEL.NS", "BANKBARODA.NS", "PNB.NS", "IOC.NS",
        "CANBK.NS", "UNIONBANK.NS", "IDBI.NS", "ABRETAIL.NS", "PAGEIND.NS", "ACC.NS", "AMBUJACEM.NS", "UBL.NS", "MCDOWELL-N.NS", "BERGEPAINT.NS",
        "COLPAL.NS", "SRF.NS", "MUTHOOTFIN.NS", "PEL.NS", "PFC.NS", "RECIND.NS", "POLYCAB.NS", "HAVELLS.NS", "KEI.NS", "CUMMINSIND.NS",
        "PERSISTENT.NS", "KPITTECH.NS", "COFORGE.NS", "MPHASIS.NS", "LTI.NS", "DIXON.NS", "ASTRAL.NS", "SUPREMEIND.NS", "BALKRISIND.NS", "MRF.NS",
        "APOLLOTYRE.NS", "CEATLTD.NS", "JKTYRE.NS", "YESBANK.NS"
    ]

    # Mapping to improve NewsAPI keyword search accuracy
    TICKER_NAME_MAP = {
        "AAPL": "Apple Inc", "MSFT": "Microsoft", "AMZN": "Amazon", "NVDA": "NVIDIA", "GOOGL": "Google Alphabet", 
        "META": "Meta Platforms", "TSLA": "Tesla", "BRK-B": "Berkshire Hathaway", "UNH": "UnitedHealth", "LLY": "Eli Lilly",
        "RELIANCE.NS": "Reliance Industries", "TCS.NS": "Tata Consultancy Services", "INFY.NS": "Infosys", "HDFCBANK.NS": "HDFC Bank", "ICICIBANK.NS": "ICICI Bank",
        "ZOMATO.NS": "Zomato", "TATAMOTORS.NS": "Tata Motors", "ADANIENT.NS": "Adani Enterprises", "BHARTIARTL.NS": "Bharti Airtel", "SBIN.NS": "State Bank of India"
        # Names are auto-resolved to ticker if missing, but these core ones improve search significantly.
    }
