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

    # NewsAPI key should be set in .env as: NEWS_API_KEY=your_key_here
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

    # Gmail SMTP (for OTP emails)
    GMAIL_SENDER = os.getenv("GMAIL_SENDER", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

    # Gemini AI Key
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # SQLite database file path
    DB_PATH = BASE_DIR / "data" / "stock_dashboard.db"

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
