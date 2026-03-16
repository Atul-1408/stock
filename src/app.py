import os
import sys
from pathlib import Path
# Fix import path for subpackages
sys.path.append(str(Path(__file__).parent))

import threading
from datetime import timedelta, datetime
import json
import pandas as pd
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import database
# ⚠️ IMPORTANT: Initialize DB tables FIRST before importing any other local modules.
# Some modules (like alert_engine) access the DB at import/class-init time.
database.init_db()

import trading_bot.main as bot
import trading_engine
import analytics_engine
import alert_engine
import leaderboard_engine
import chatbot_engine
import error_handler
from trading_bot.bot_engine import bot_engine

# Configure Flask
app = Flask(
    __name__,
    static_folder=os.path.join("..", "frontend", "dist")
)
app.url_map.strict_slashes = False

# Production Setup
error_handler.setup_logging(app)
error_handler.register_error_handlers(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'sovereign-intelligence-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
jwt = JWTManager(app)

CORS(app)

@app.after_request
def after_request(response):
    response.headers.add('Cross-Origin-Opener-Policy', 'same-origin-allow-popups')
    return response


# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5000 per day", "500 per hour"],
    storage_uri="memory://"
)

# In-memory cache for high-traffic public endpoints
_ticker_tape_cache = {
    "ts": 0.0,
    "key": None,
    "payload": None,
}

_currency_list_cache = {
    "ts": 0.0,
    "payload": None,
}

_currency_rates_cache = {
    "ts": 0.0,
    "payload": None,
}

# ==========================================
# TRADING BOT INTEGRATION
# ==========================================
def start_bot():
    """Starts the trading bot in a background thread."""
    try:
        bot.init_trading_system()
        bot.run_bot_engine()
    except Exception as e:
        app.logger.error(f"Bot Startup Error: {str(e).encode('ascii', 'ignore').decode()}")

# Initialize Database first
database.init_db()

# Start bot thread
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

# Start market data feed
try:
    from market_data_feed import market_feed
    market_feed.start()
except Exception as e:
    print(f"Market feed start error: {e}")

# Start currency converter with auto-update
try:
    from currency_converter import currency_converter
    currency_converter.start_auto_update()
except Exception as e:
    print(f"Currency converter start error: {e}")

def error_response(message: str, status_code: int = 400):
    """Return a standardized JSON error response."""
    return jsonify({"status": "error", "message": message}), status_code

# --- Existing Routes (Now Protected) ---
@app.route('/api/ticker-tape', methods=['GET'])
@limiter.limit("300 per minute")
def get_ticker_tape():
    """Return live prices for all requested tickers. No auth needed (public route)."""
    tickers_param = request.args.get('tickers', '')
    if not tickers_param:
        return jsonify({"tickers": []}), 200

    ticker_list = [t.strip().upper() for t in tickers_param.split(',') if t.strip()][:30]

    # Short cache window to prevent repeated fetches (e.g., StrictMode double-mount)
    cache_key = ",".join(sorted(ticker_list))
    now_ts = datetime.now().timestamp()
    if (
        _ticker_tape_cache.get("payload") is not None
        and _ticker_tape_cache.get("key") == cache_key
        and (now_ts - float(_ticker_tape_cache.get("ts") or 0.0)) < 15.0
    ):
        return jsonify(_ticker_tape_cache["payload"]), 200

    results = []
    finnhub_key = os.getenv('FINNHUB_API_KEY', '').strip()

    def _to_finnhub_symbol(raw: str):
        s = (raw or '').strip().upper()
        # Skip Indian Yahoo-style symbols (Finnhub availability varies heavily by plan)
        if s.endswith('.NS') or s.endswith('.BO'):
            return None

        # Crypto mapping
        # Accept: BTC-USD, BTC/USD, BTCUSDT, BTC-USD, ETH-USD etc.
        base = None
        quote = None
        if '/' in s:
            parts = s.split('/')
            if len(parts) == 2:
                base, quote = parts[0], parts[1]
        elif '-' in s:
            parts = s.split('-')
            if len(parts) == 2:
                base, quote = parts[0], parts[1]
        else:
            # Compact crypto like BTCUSDT
            if len(s) >= 6 and s.endswith('USDT'):
                base, quote = s[:-4], 'USDT'
            elif len(s) >= 6 and s.endswith('USD'):
                base, quote = s[:-3], 'USD'

        if base and quote:
            # Finnhub crypto quotes typically use exchange prefix like BINANCE:BTCUSDT
            q = 'USDT' if quote == 'USD' else quote
            return f'BINANCE:{base}{q}'

        # Default: treat as equity/forex symbol and pass through
        return s

    def _append_quote(ticker: str, price, prev_close):
        if price is None:
            results.append({"ticker": ticker, "price": None, "change": None, "changePct": None})
            return
        try:
            price_f = float(price)
        except Exception:
            results.append({"ticker": ticker, "price": None, "change": None, "changePct": None})
            return
        prev_f = None
        try:
            prev_f = float(prev_close) if prev_close is not None else None
        except Exception:
            prev_f = None

        if prev_f is None or prev_f == 0:
            change = None
            change_pct = None
        else:
            change = price_f - prev_f
            change_pct = (change / prev_f * 100)

        results.append({
            "ticker": ticker,
            "price": round(price_f, 2),
            "change": round(change, 2) if change is not None else None,
            "changePct": round(change_pct, 2) if change_pct is not None else None,
        })

    # 1) Try Finnhub (near real-time) when configured
    if finnhub_key:
        try:
            import requests as req
            for ticker in ticker_list:
                try:
                    finnhub_symbol = _to_finnhub_symbol(ticker)
                    if not finnhub_symbol:
                        raise Exception("Skip Finnhub")
                    r = req.get(
                        'https://finnhub.io/api/v1/quote',
                        params={'symbol': finnhub_symbol, 'token': finnhub_key},
                        timeout=6,
                    )
                    if r.status_code != 200:
                        raise Exception(f"Finnhub status {r.status_code}")
                    q = r.json() or {}
                    # Finnhub fields: c=current, pc=previous close
                    cur = q.get('c')
                    pc = q.get('pc')
                    if cur is None or float(cur or 0) <= 0:
                        # Symbol unsupported or no quote; fallback to yfinance below
                        raise Exception("No quote")
                    _append_quote(ticker, cur, pc)
                except Exception:
                    _append_quote(ticker, None, None)
        except Exception as e:
            app.logger.warning(f"Finnhub ticker fetch error: {e}")
            results = []

    # 2) Fallback to yfinance for any missing tickers or when Finnhub not configured
    missing = [r["ticker"] for r in results if r.get("price") is None]
    if (not finnhub_key) or missing or not results:
        # Ensure we preserve any Finnhub successes and only fill in missing
        existing_map = {r["ticker"]: r for r in results}
        try:
            import yfinance as yf
            yf_list = missing if finnhub_key else ticker_list
            if yf_list:
                data = yf.download(yf_list, period="2d", interval="1d", progress=False, group_by='ticker')
                for ticker in yf_list:
                    try:
                        if len(yf_list) == 1:
                            df = data
                        else:
                            df = data[ticker] if ticker in data.columns.get_level_values(0) else None

                        if df is None or df.empty or len(df) < 1:
                            existing_map[ticker] = {"ticker": ticker, "price": None, "change": None, "changePct": None}
                            continue

                        close_vals = df['Close'].dropna()
                        if len(close_vals) < 1:
                            existing_map[ticker] = {"ticker": ticker, "price": None, "change": None, "changePct": None}
                            continue

                        last_close = float(close_vals.iloc[-1])
                        prev_close = float(close_vals.iloc[-2]) if len(close_vals) >= 2 else last_close
                        change = last_close - prev_close
                        change_pct = (change / prev_close * 100) if prev_close != 0 else 0

                        existing_map[ticker] = {
                            "ticker": ticker,
                            "price": round(last_close, 2),
                            "change": round(change, 2),
                            "changePct": round(change_pct, 2),
                        }
                    except Exception:
                        existing_map[ticker] = {"ticker": ticker, "price": None, "change": None, "changePct": None}

            results = [existing_map[t] for t in ticker_list]
        except Exception as e:
            app.logger.warning(f"Ticker tape fetch error: {e}")
            results = [{"ticker": t, "price": None, "change": None, "changePct": None} for t in ticker_list]

    payload = {"tickers": results}
    _ticker_tape_cache["ts"] = now_ts
    _ticker_tape_cache["key"] = cache_key
    _ticker_tape_cache["payload"] = payload
    return jsonify(payload), 200


@app.route("/health", methods=["GET"])
def health() -> tuple:
    return jsonify({"status": "ok", "service": "stock-sentiment-api", "bot_active": bot_thread.is_alive()}), 200


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================
@app.route('/api/auth/signup', methods=['POST'])
@limiter.limit("5 per hour")
def signup():
    print(f"DEBUG: Signup request received for {request.json.get('email')}")
    data = request.json
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')
    full_name = data.get('full_name')

    if not email or not password:
        return error_response("Email and password are required.", 400)

    if database.get_user_by_email(email):
        return error_response("User with this email already exists.", 409)

    hashed_password = generate_password_hash(password)
    user_id = database.create_user(email, hashed_password, username, full_name)

    if user_id:
        access_token = create_access_token(identity=str(user_id))
        return jsonify({"status": "success", "access_token": access_token, "user_id": user_id}), 201
    else:
        return error_response("Failed to create user.", 500)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per hour")
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return error_response("Email and password are required.", 400)

    user = database.get_user_by_email(email)
    if not user or user['password_hash'] == '__GOOGLE_AUTH__' or not check_password_hash(user['password_hash'], password):
        return error_response("Invalid email or password.", 401)

    access_token = create_access_token(identity=str(user['id']))
    return jsonify({"status": "success", "access_token": access_token, "user_id": user['id']}), 200

# ---- OTP Login Routes ----
@app.route('/api/auth/otp/send', methods=['POST'])
@limiter.limit("5 per minute")
def send_otp():
    import otp_service
    data = request.json
    email = data.get('email')
    if not email:
        return error_response("Email is required.", 400)

    code = otp_service.generate_otp()
    expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    database.save_otp(email, code, expires_at)

    sent = otp_service.send_otp_email(email, code)
    if sent:
        return jsonify({"status": "success", "message": "OTP sent to your email."}), 200
    else:
        return error_response("Failed to send OTP. Please try again.", 500)

@app.route('/api/auth/otp/verify', methods=['POST'])
@limiter.limit("10 per minute")
def verify_otp_route():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    if not email or not otp:
        return error_response("Email and OTP are required.", 400)

    if not database.verify_otp(email, otp):
        return error_response("Invalid or expired OTP.", 401)

    # OTP valid — find or create user 
    user = database.get_user_by_email(email)
    if not user:
        # Auto-create account for OTP login (no password needed)
        user_id = database.create_user(email, '__OTP_AUTH__', email.split('@')[0])
        user = database.get_user_by_id(user_id)

    access_token = create_access_token(identity=str(user['id']))
    return jsonify({"status": "success", "access_token": access_token, "user_id": user['id']}), 200

# ---- Google OAuth Route ----
@app.route('/api/auth/google', methods=['POST'])
@limiter.limit("10 per minute")
def google_auth():
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from config import Config

    data = request.json
    credential = data.get('credential')
    if not credential:
        return error_response("Google credential is required.", 400)

    try:
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), Config.GOOGLE_CLIENT_ID)
        google_email = idinfo.get('email')
        google_name = idinfo.get('name', '')

        if not google_email:
            return error_response("Could not get email from Google.", 400)

        user = database.create_or_get_google_user(google_email, google_name)
        if not user:
            return error_response("Failed to create/find user.", 500)

        access_token = create_access_token(identity=str(user['id']))
        return jsonify({"status": "success", "access_token": access_token, "user_id": user['id']}), 200
    except ValueError as e:
        return error_response(f"Invalid Google token: {str(e)}", 401)

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = int(get_jwt_identity())
    user = database.get_user_by_id(user_id)
    if not user:
        return error_response("User not found.", 404)
    
    user_data = {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "full_name": user["full_name"],
        "current_balance": user["current_balance"]
    }
    return jsonify({"status": "success", "user": user_data}), 200

# ==========================================
# BOT SYSTEM API ROUTES
# ==========================================

@app.route('/api/bot/config', methods=['GET'])
@jwt_required()
def get_bot_config():
    """Get user's bot configuration"""
    user_id = int(get_jwt_identity())
    
    config = database.get_bot_config(user_id)
    
    if not config:
        # Create default config
        database.create_bot_config(user_id)
        config = database.get_bot_config(user_id)
    
    return jsonify({'config': config}), 200

@app.route('/api/bot/config', methods=['PUT'])
@jwt_required()
def update_bot_config():
    """Update bot configuration"""
    user_id = int(get_jwt_identity())
    data = request.json
    
    database.update_bot_config(user_id, data)
    
    return jsonify({'success': True}), 200

@app.route('/api/bot/start', methods=['POST'])
@jwt_required()
def activate_bot_api():
    """Activate bot"""
    user_id = int(get_jwt_identity())
    
    database.set_bot_active(user_id, True)
    bot_engine.start()
    
    return jsonify({'success': True, 'message': 'Bot activated'}), 200

@app.route('/api/bot/stop', methods=['POST'])
@jwt_required()
def stop_bot_api():
    """Deactivate bot"""
    user_id = int(get_jwt_identity())
    
    database.set_bot_active(user_id, False)
    
    return jsonify({'success': True, 'message': 'Bot stopped'}), 200

@app.route('/api/bot/watchlist', methods=['GET'])
@jwt_required()
def get_bot_watchlist():
    """Get bot watchlist"""
    user_id = int(get_jwt_identity())
    
    watchlist = database.get_bot_watchlist(user_id)
    
    return jsonify({'watchlist': watchlist}), 200

@app.route('/api/bot/watchlist', methods=['POST'])
@jwt_required()
def add_to_watchlist():
    """Add stock to bot watchlist"""
    user_id = int(get_jwt_identity())
    data = request.json
    
    ticker = data.get('ticker')
    
    try:
        database.add_to_bot_watchlist(user_id, ticker)
        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'error': 'Already in watchlist'}), 400

@app.route('/api/bot/watchlist/<ticker>', methods=['DELETE'])
@jwt_required()
def remove_from_watchlist(ticker):
    """Remove from watchlist"""
    user_id = int(get_jwt_identity())
    
    database.remove_from_bot_watchlist(user_id, ticker)
    
    return jsonify({'success': True}), 200

@app.route('/api/bot/signals', methods=['GET'])
@jwt_required()
def get_bot_signals():
    """Get recent bot signals"""
    user_id = int(get_jwt_identity())
    limit = request.args.get('limit', 20, type=int)
    
    signals = database.get_bot_signals(user_id, limit)
    
    return jsonify({'signals': signals}), 200

@app.route('/api/bot/trades', methods=['GET'])
@jwt_required()
def get_bot_trades():
    """Get bot trade history"""
    user_id = int(get_jwt_identity())
    
    trades = database.get_transactions_by_user(user_id, limit=100)
    return jsonify({'trades': trades}), 200

@app.route('/api/bot/performance', methods=['GET'])
@jwt_required()
def get_bot_performance():
    """Get bot performance metrics"""
    user_id = int(get_jwt_identity())
    
    trades = database.get_closed_trades(user_id)
    
    if not trades:
        return jsonify({
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_profit': 0,
            'avg_loss': 0
        }), 200
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
    losing_trades = total_trades - winning_trades
    
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    profits = [t['pnl'] for t in trades if t.get('pnl', 0) > 0]
    losses = [t['pnl'] for t in trades if t.get('pnl', 0) < 0]
    
    avg_profit = sum(profits) / len(profits) if profits else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    
    return jsonify({
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 2),
        'total_pnl': round(total_pnl, 2),
        'avg_profit': round(avg_profit, 2),
        'avg_loss': round(avg_loss, 2)
    }), 200

@app.route('/api/bot/status', methods=['GET'])
@jwt_required()
def get_bot_status():
    """Get complete bot status"""
    user_id = int(get_jwt_identity())
    
    config = database.get_bot_config(user_id)
    watchlist = database.get_bot_watchlist(user_id)
    signals = database.get_bot_signals(user_id, 5)
    open_positions = database.get_open_bot_trades(user_id)
    
    return jsonify({
        'is_active': config.get('is_active', False) if config else False,
        'config': config if config else {},
        'watchlist': [w.get('ticker') for w in watchlist] if watchlist else [],
        'recent_signals': signals if signals else [],
        'open_positions': open_positions if open_positions else []
    }), 200

# ==========================================
# TRADING ENGINE ROUTES
# ==========================================
@app.route('/api/trade', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def make_trade():
    user_id = int(get_jwt_identity())
    data = request.json
    
    ticker = data.get('ticker')
    action = data.get('action') 
    shares = data.get('shares')
    sentiment_score = data.get('sentiment_score')
    sentiment_label = data.get('sentiment_label')
    
    if not ticker or not action or shares is None:
        return error_response("Ticker, action, and shares are required.", 400)
    
    result = trading_engine.execute_trade(user_id, ticker, action, float(shares), sentiment_score, sentiment_label)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return error_response(result['message'], 400)

@app.route('/api/portfolio', methods=['GET'])
@jwt_required()
def get_portfolio():
    user_id = int(get_jwt_identity())
    summary = trading_engine.get_portfolio_summary(user_id)
    return jsonify({"status": "success", "data": summary}), 200

@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = int(get_jwt_identity())
    limit = request.args.get('limit', default=50, type=int)
    transactions = database.get_transactions_by_user(user_id, limit)
    return jsonify({"status": "success", "data": transactions}), 200

@app.route('/api/balance', methods=['GET'])
@jwt_required()
def get_balance_route():
    user_id = int(get_jwt_identity())
    balance = database.get_user_balance(user_id)
    return jsonify({"status": "success", "balance": balance}), 200

# ==========================================
# STOCK DATA ROUTES (needed by Dashboard.jsx)
# ==========================================
@app.route('/api/sentiment/<ticker>', methods=['GET'])
@jwt_required()
@limiter.limit("60 per minute")
def get_sentiment_for_ticker(ticker):
    """Return the last 30 days of sentiment data for a ticker."""
    ticker = ticker.upper()
    data = database.get_sentiments_last_30_days(ticker)
    if data:
        return jsonify({"status": "success", "data": data}), 200

    # Live fallback when pipeline hasn't populated DB (common for crypto tickers)
    try:
        from datetime import datetime, timezone
        import yfinance as yf
        from sentiment_service import SentimentAnalyzer
        from config import Config
        from news_fetcher import fetch_news_for_ticker

        analyzer = SentimentAnalyzer()

        articles = []
        try:
            yf_news = yf.Ticker(ticker).news or []
            for n in yf_news[:10]:
                articles.append(
                    {
                        "title": n.get("title", ""),
                        "url": n.get("link", ""),
                        "source": n.get("publisher", ""),
                        "published_at": n.get("providerPublishTime", ""),
                    }
                )
        except Exception as e:
            app.logger.warning(f"Live yfinance news fallback error for {ticker}: {e}")

        if not articles and Config.NEWS_API_KEY:
            try:
                articles = fetch_news_for_ticker(ticker)[:10]
            except Exception as e:
                app.logger.warning(f"Live NewsAPI fallback error for {ticker}: {e}")

        # Finnhub fallback (helps a lot for crypto tickers where yfinance returns no news)
        if not articles:
            finnhub_key = os.getenv('FINNHUB_API_KEY', '').strip()
            if finnhub_key:
                try:
                    import requests as req

                    # Finnhub free tiers often support crypto category news.
                    r = req.get(
                        'https://finnhub.io/api/v1/news',
                        params={'category': 'crypto', 'token': finnhub_key},
                        timeout=8,
                    )
                    if r.status_code == 200:
                        items = r.json() or []
                        # Keep it simple: take top 10 crypto headlines.
                        for it in items[:10]:
                            articles.append(
                                {
                                    'title': it.get('headline', '') or '',
                                    'url': it.get('url', '') or '',
                                    'source': it.get('source', '') or '',
                                    'published_at': it.get('datetime', '') or '',
                                }
                            )
                    else:
                        app.logger.warning(f"Finnhub news status {r.status_code} for {ticker}")
                except Exception as e:
                    app.logger.warning(f"Finnhub crypto news fallback error for {ticker}: {e}")

        analyzed_at = datetime.now(timezone.utc).isoformat()
        live_data = []
        for a in articles:
            title = (a.get("title") or "").strip()
            result = analyzer.analyze_headline(title)
            live_data.append(
                {
                    "ticker": ticker,
                    "title": title,
                    "url": a.get("url", ""),
                    "published_at": a.get("published_at", ""),
                    "sentiment_label": result.get("label", "Neutral"),
                    "sentiment_score": float(result.get("score", 0.0)),
                    "model_name": result.get("model", "vader"),
                    "analyzed_at": analyzed_at,
                }
            )

        return jsonify({"status": "success", "data": live_data}), 200
    except Exception as e:
        app.logger.warning(f"Sentiment live fallback error for {ticker}: {e}")
        return jsonify({"status": "success", "data": []}), 200

@app.route('/api/prices/<ticker>', methods=['GET'])
@jwt_required()
@limiter.limit("60 per minute")
def get_prices_for_ticker(ticker):
    """Return the last 30 days of price data for a ticker."""
    ticker = ticker.upper()
    data = database.get_prices_last_30_days(ticker)
    # If no cached data, fetch live from yfinance
    if not data:
        try:
            import yfinance as yf
            df = yf.download(ticker, period="30d", interval="1d", progress=False)
            if not df.empty:
                if hasattr(df.columns, 'droplevel'):
                    try:
                        df.columns = df.columns.droplevel(1)
                    except Exception:
                        pass
                data = [
                    {"trade_date": str(idx.date()), "close": float(row["Close"])}
                    for idx, row in df.iterrows()
                ]
        except Exception as e:
            app.logger.warning(f"Price fetch error for {ticker}: {e}")
    return jsonify({"status": "success", "data": data}), 200

@app.route('/api/news/<ticker>', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_news_for_ticker(ticker):
    """Return recent news with sentiment for a ticker."""
    ticker = ticker.upper()
    data = database.get_news_with_latest_sentiment(ticker)
    # If no cached news, return live headlines (yfinance first, then NewsAPI)
    if not data:
        try:
            from datetime import datetime, timezone
            import yfinance as yf
            from sentiment_service import SentimentAnalyzer
            from config import Config
            from news_fetcher import fetch_news_for_ticker

            analyzer = SentimentAnalyzer()
            articles = []

            try:
                news_items = yf.Ticker(ticker).news or []
                for n in news_items[:10]:
                    articles.append(
                        {
                            "title": n.get("title", ""),
                            "url": n.get("link", ""),
                            "source": n.get("publisher", ""),
                            "published_at": n.get("providerPublishTime", ""),
                            "description": n.get("summary", ""),
                        }
                    )
            except Exception as e:
                app.logger.warning(f"Live yfinance news error for {ticker}: {e}")

            if not articles and Config.NEWS_API_KEY:
                try:
                    articles = fetch_news_for_ticker(ticker)[:10]
                except Exception as e:
                    app.logger.warning(f"Live NewsAPI error for {ticker}: {e}")

            # Finnhub fallback (useful for crypto)
            if not articles:
                finnhub_key = os.getenv('FINNHUB_API_KEY', '').strip()
                if finnhub_key:
                    try:
                        import requests as req
                        r = req.get(
                            'https://finnhub.io/api/v1/news',
                            params={'category': 'crypto', 'token': finnhub_key},
                            timeout=8,
                        )
                        if r.status_code == 200:
                            items = r.json() or []
                            for it in items[:10]:
                                articles.append(
                                    {
                                        'title': it.get('headline', '') or '',
                                        'url': it.get('url', '') or '',
                                        'source': it.get('source', '') or '',
                                        'published_at': it.get('datetime', '') or '',
                                        'description': it.get('summary', '') or '',
                                    }
                                )
                        else:
                            app.logger.warning(f"Finnhub news status {r.status_code} for {ticker}")
                    except Exception as e:
                        app.logger.warning(f"Finnhub crypto news fallback error for {ticker}: {e}")

            analyzed_at = datetime.now(timezone.utc).isoformat()
            data = []
            for a in articles:
                title = (a.get("title") or "").strip()
                result = analyzer.analyze_headline(title)
                data.append(
                    {
                        "title": title,
                        "url": a.get("url", ""),
                        "source": a.get("source", ""),
                        "published_at": a.get("published_at", ""),
                        "description": a.get("description", ""),
                        "sentiment_label": result.get("label", "Neutral"),
                        "sentiment_score": float(result.get("score", 0.0)),
                        "model_name": result.get("model", "vader"),
                        "analyzed_at": analyzed_at,
                    }
                )
        except Exception as e:
            app.logger.warning(f"News live fallback error for {ticker}: {e}")
            data = []
    return jsonify({"status": "success", "data": data}), 200

@app.route('/api/stock/<ticker>', methods=['GET'])
@jwt_required()
def get_stock_analysis(ticker):
    price_history = database.get_prices_last_30_days(ticker)
    sentiment_history = database.get_sentiments_last_30_days(ticker)
    latest_news = database.get_news_with_latest_sentiment(ticker)
    
    return jsonify({
        "status": "success",
        "ticker": ticker.upper(),
        "price_history": price_history,
        "sentiment_history": sentiment_history,
        "latest_news": latest_news
    }), 200

@app.route('/api/profile/update', methods=['POST'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    data = request.json
    database.update_user_profile(
        user_id, 
        data.get('bio', ''), 
        data.get('avatar_url', ''), 
        data.get('is_public', True), 
        data.get('twitter_handle', '')
    )
    return jsonify({"status": "success", "message": "Profile updated."}), 200

@app.route('/api/profile/summary/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_summary(user_id):
    user = database.get_user_by_id(user_id)
    if not user: return error_response("User not found", 404)
    
    return jsonify({
        'username': user['username'],
        'full_name': user['full_name'],
        'avatar_url': user.get('avatar_url'),
        'followers': database.get_follower_count(user_id),
        'following': database.get_following_count(user_id)
    }), 200


@app.route('/api/analytics/overview', methods=['GET'])
@jwt_required()
def get_analytics_overview_api():
    user_id = int(get_jwt_identity())
    data = analytics_engine.calculate_portfolio_performance(user_id)
    return jsonify(data), 200


@app.route('/api/analytics/history', methods=['GET'])
@jwt_required()
def get_analytics_history_api():
    user_id = int(get_jwt_identity())
    days = request.args.get('days', default=30, type=int)
    history = analytics_engine.get_portfolio_history(user_id, days=days)

    if days and isinstance(days, int) and days > 0:
        dates = history.get('dates', [])
        values = history.get('values', [])
        benchmark_values = history.get('benchmark_values', [])
        if len(dates) > days:
            history['dates'] = dates[-days:]
            history['values'] = values[-days:]
            history['benchmark_values'] = benchmark_values[-days:]

    return jsonify(history), 200


@app.route('/api/analytics/sectors', methods=['GET'])
@jwt_required()
def get_analytics_sectors_api():
    user_id = int(get_jwt_identity())
    data = analytics_engine.get_sector_allocation(user_id)
    return jsonify(data), 200


@app.route('/api/analytics/risk', methods=['GET'])
@jwt_required()
def get_analytics_risk_api():
    user_id = int(get_jwt_identity())
    data = analytics_engine.get_risk_metrics(user_id)
    return jsonify(data), 200


@app.route('/api/analytics/top-performers', methods=['GET'])
@jwt_required()
def get_analytics_top_performers_api():
    user_id = int(get_jwt_identity())
    portfolio = database.get_user_portfolio(user_id)
    performers = []
    for holding in portfolio:
        ticker = holding.get('ticker')
        shares = float(holding.get('shares', 0) or 0)
        avg_buy_price = float(holding.get('avg_buy_price', 0) or 0)
        if not ticker or shares <= 0 or avg_buy_price <= 0:
            continue

        current_price = trading_engine.get_current_price(ticker)
        invested = shares * avg_buy_price
        current_value = shares * current_price
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0

        performers.append({
            'ticker': ticker,
            'shares': shares,
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
        })

    performers.sort(key=lambda x: x['pnl_pct'], reverse=True)
    top = performers[:5]
    worst = list(reversed(performers[-5:])) if performers else []
    return jsonify({'top_performers': top, 'worst_performers': worst}), 200

# ==========================================
# ALERT MANAGEMENT ROUTES
# ==========================================
@app.route('/api/alerts', methods=['GET'])
@jwt_required()
def get_user_alerts():
    user_id = int(get_jwt_identity())
    alerts = database.get_alert_rules(user_id)
    return jsonify({'alerts': alerts}), 200

@app.route('/api/alerts', methods=['POST'])
@jwt_required()
def create_alert():
    user_id = int(get_jwt_identity())
    data = request.json
    alert_id = database.create_alert_rule(user_id, data['ticker'], data['alert_type'], data.get('condition_operator'), data.get('threshold_value'), data.get('notification_method', 'email'))
    return jsonify({'success': True, 'alert_id': alert_id}), 201

@app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
@jwt_required()
def delete_alert(alert_id):
    user_id = int(get_jwt_identity())
    if not database.verify_alert_ownership(alert_id, user_id): return error_response("Unauthorized", 403)
    database.delete_alert_rule(alert_id)
    return jsonify({'success': True}), 200

@app.route('/api/alerts/<int:alert_id>/toggle', methods=['PUT'])
@jwt_required()
def toggle_alert(alert_id):
    user_id = int(get_jwt_identity())
    if not database.verify_alert_ownership(alert_id, user_id): return error_response("Unauthorized", 403)
    database.toggle_alert_rule(alert_id, request.json.get('is_active'))
    return jsonify({'success': True}), 200


@app.route('/api/alerts/history', methods=['GET'])
@jwt_required()
def get_alert_history_api():
    user_id = int(get_jwt_identity())
    logs = database.get_alert_logs(user_id)
    return jsonify({'logs': logs}), 200


@app.route('/api/alerts/history/<int:log_id>/read', methods=['PUT'])
@jwt_required()
def mark_alert_history_read_api(log_id):
    user_id = int(get_jwt_identity())
    database.mark_alert_log_read(log_id, user_id)
    return jsonify({'success': True}), 200

@app.route('/api/alerts/bot', methods=['GET'])
def get_bot_alerts_api():
    alerts = database.get_bot_alerts(limit=30)
    return jsonify({'alerts': alerts}), 200

@app.route('/api/alerts/bot-clear', methods=['DELETE'])
@jwt_required()
def clear_bot_alerts_api():
    database.clear_bot_alerts()
    return jsonify({'success': True}), 200

# ==========================================
# CHATBOT ROUTES
# ==========================================
@app.route('/api/chat/conversations', methods=['GET'])
@jwt_required()
def get_chat_conversations_api():
    user_id = int(get_jwt_identity())
    conversations = database.get_user_conversations(user_id)
    return jsonify({'conversations': conversations}), 200

@app.route('/api/chat/conversation', methods=['POST'])
@jwt_required()
def create_conversation_api():
    user_id = int(get_jwt_identity())
    title = request.json.get('title', f"Chat {datetime.now().strftime('%d/%m %H:%M')}")
    conv_id = database.create_new_conversation(user_id, title)
    return jsonify({'conversation_id': conv_id, 'title': title}), 201

@app.route('/api/chat/<int:conversation_id>/messages', methods=['GET'])
@jwt_required()
def get_conversation_messages_api(conversation_id):
    user_id = int(get_jwt_identity())
    if not database.verify_conversation_ownership(conversation_id, user_id): return error_response("Unauthorized", 403)
    messages = database.get_conversation_history(conversation_id)
    return jsonify({'messages': messages}), 200

@app.route('/api/chat/<int:conversation_id>/message', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def send_chat_message_api(conversation_id):
    user_id = int(get_jwt_identity())
    user_message = request.json.get('message')
    if not user_message: return error_response("Message required", 400)
    if not database.verify_conversation_ownership(conversation_id, user_id): return error_response("Unauthorized", 403)
    
    history = database.get_conversation_history(conversation_id)
    database.save_chat_message(conversation_id, 'user', user_message)
    
    response = chatbot_engine.chatbot.get_response(user_id, user_message, history)
    database.save_chat_message(conversation_id, 'assistant', response['response'], stocks_mentioned=response['stocks_mentioned'])
    
    return jsonify(response), 200

@app.route('/api/chat/analyze/<ticker>', methods=['GET'])
@jwt_required()
def chat_analyze_stock_api(ticker):
    analysis = chatbot_engine.chatbot.analyze_stock_for_chat(ticker.upper())
    return jsonify({'analysis': analysis}), 200

# ==========================================
# LEADERBOARD & SOCIAL ROUTES
# ==========================================
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard_api():
    period = request.args.get('period', 'all_time')
    board = leaderboard_engine.get_global_leaderboard(period)
    return jsonify({'leaderboard': board}), 200


@app.route('/api/leaderboard/my-rank', methods=['GET'])
@jwt_required()
def get_my_rank_api():
    user_id = int(get_jwt_identity())
    period = request.args.get('period', 'all_time')
    rank = leaderboard_engine.get_user_rank(user_id, period)
    return jsonify({'rank': rank}), 200

@app.route('/api/social/follow/<int:following_id>', methods=['POST'])
@jwt_required()
def follow_user_api(following_id):
    follower_id = int(get_jwt_identity())
    database.create_follow(follower_id, following_id)
    return jsonify({'success': True}), 201

@app.route('/api/social/unfollow/<int:following_id>', methods=['POST'])
@jwt_required()
def unfollow_user_api(following_id):
    follower_id = int(get_jwt_identity())
    database.remove_follow(follower_id, following_id)
    return jsonify({'success': True}), 200

@app.route('/api/social/share', methods=['POST'])
@jwt_required()
def share_trade_api():
    user_id = int(get_jwt_identity())
    d = request.json
    trade_id = database.create_shared_trade(user_id, d['ticker'], d['action'], d['entry'], d['target'], d['sentiment'], d['reasoning'])
    return jsonify({'trade_id': trade_id}), 201

@app.route('/api/social/trades', methods=['GET'])
def get_social_feed_api():
    trades = leaderboard_engine.get_social_feed()
    return jsonify({'trades': trades}), 200

@app.route('/api/social/trades/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_trades_api(user_id):
    trades = database.get_user_shared_trades(user_id)
    return jsonify(trades), 200

@app.route('/api/social/like/<int:trade_id>', methods=['POST'])
@jwt_required()
def like_trade_api(trade_id):
    user_id = int(get_jwt_identity())
    database.create_trade_like(trade_id, user_id)
    database.update_likes_count(trade_id)
    return jsonify({'success': True}), 200

@app.route('/api/social/comment/<int:trade_id>', methods=['POST'])
@jwt_required()
def comment_trade_api(trade_id):
    user_id = int(get_jwt_identity())
    text = request.json.get('comment')
    comment_id = database.create_trade_comment(trade_id, user_id, text)
    database.update_comments_count(trade_id)
    return jsonify({'comment_id': comment_id}), 201

# ==========================================
# CURRENCY API ROUTES
# ==========================================

@app.route('/api/currency/list', methods=['GET'])
@limiter.exempt
def get_currencies_list():
    """Get all available currencies."""
    now_ts = datetime.now().timestamp()
    if (
        _currency_list_cache.get("payload") is not None
        and (now_ts - float(_currency_list_cache.get("ts") or 0.0)) < 300.0
    ):
        return jsonify(_currency_list_cache["payload"]), 200

    currencies = database.get_all_currencies()
    payload = {'currencies': currencies}
    _currency_list_cache["ts"] = now_ts
    _currency_list_cache["payload"] = payload
    return jsonify(payload), 200


@app.route('/api/currency/detect', methods=['GET'])
@limiter.limit("30 per hour")
def detect_currency():
    """Auto-detect user's currency based on IP."""
    COUNTRY_MAP = {
        'US': 'USD', 'IN': 'INR', 'GB': 'GBP', 'DE': 'EUR', 'FR': 'EUR',
        'IT': 'EUR', 'ES': 'EUR', 'JP': 'JPY', 'AU': 'AUD', 'CA': 'CAD',
        'CH': 'CHF', 'CN': 'CNY', 'SG': 'SGD', 'HK': 'HKD', 'AE': 'AED',
        'BR': 'BRL', 'MX': 'MXN', 'ZA': 'ZAR',
    }
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    try:
        import requests as req
        resp = req.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            cc = data.get('countryCode', 'US')
            return jsonify({
                'country_code': cc,
                'country_name': data.get('country', 'Unknown'),
                'currency': COUNTRY_MAP.get(cc, 'USD'),
                'timezone': data.get('timezone', 'UTC'),
            }), 200
    except Exception:
        pass
    return jsonify({'country_code': 'US', 'currency': 'USD', 'timezone': 'UTC'}), 200


@app.route('/api/currency/rates', methods=['GET'])
@limiter.exempt
def get_exchange_rates():
    """Get all USD-based exchange rates for client-side conversion."""
    now_ts = datetime.now().timestamp()
    if (
        _currency_rates_cache.get("payload") is not None
        and (now_ts - float(_currency_rates_cache.get("ts") or 0.0)) < 300.0
    ):
        return jsonify(_currency_rates_cache["payload"]), 200
    try:
        from currency_converter import currency_converter as cc
        # Build rates dict: { "INR": 90.97, "EUR": 0.92, ... }
        rates = {}
        for key, rate in cc.cache.items():
            if key.startswith('USD_'):
                to_code = key[4:]
                rates[to_code] = rate
        rates['USD'] = 1.0
        payload = {'base': 'USD', 'rates': rates}
        _currency_rates_cache["ts"] = now_ts
        _currency_rates_cache["payload"] = payload
        return jsonify(payload), 200
    except ImportError:
        return error_response('Currency converter not available', 500)


@app.route('/api/currency/convert', methods=['POST'])
def convert_currency_api():
    """Convert amount between currencies."""
    try:
        from currency_converter import currency_converter as cc
    except ImportError:
        return error_response('Currency converter not available', 500)
    data = request.json
    amount = data.get('amount', 0)
    from_c = data.get('from', 'USD')
    to_c = data.get('to', 'INR')
    try:
        converted = cc.convert(amount, from_c, to_c)
        return jsonify({
            'original': amount, 'from': from_c, 'to': to_c,
            'converted': round(converted, 4),
            'formatted': cc.format_currency(converted, to_c),
            'rate': cc.get_rate(from_c, to_c),
        }), 200
    except Exception as e:
        return error_response(str(e), 400)


@app.route('/api/user/currency', methods=['PUT'])
@jwt_required()
def update_user_currency():
    """Update user's preferred currency."""
    user_id = int(get_jwt_identity())
    currency = request.json.get('currency', 'USD')
    database.set_user_preferred_currency(user_id, currency)
    return jsonify({'status': 'success', 'currency': currency}), 200


@app.route('/api/user/currency', methods=['GET'])
@jwt_required()
def get_user_currency():
    """Get user's preferred currency."""
    user_id = int(get_jwt_identity())
    currency = database.get_user_preferred_currency(user_id)
    return jsonify({'currency': currency}), 200


# ==========================================
# BROKER-STYLE MARKET ROUTES
# ==========================================

@app.route('/api/market/watch', methods=['GET'])
def get_market_watch():
    """Get market watchlist with filters and optional currency conversion."""
    exchange = request.args.get('exchange', 'all')
    sector = request.args.get('sector', 'all')
    search = request.args.get('search', '')
    limit = request.args.get('limit', 50, type=int)
    target_currency = request.args.get('currency', '')  # optional conversion

    stocks = database.search_stock_universe(search, exchange, sector, limit)
    symbols = [s['symbol'] for s in stocks]
    market_data_list = database.get_market_data_bulk(symbols)
    market_map = {m['symbol']: m for m in market_data_list}

    # Try to load converter for currency conversion
    cc = None
    if target_currency:
        try:
            from currency_converter import currency_converter as cc_mod
            cc = cc_mod
        except ImportError:
            pass

    for stock in stocks:
        md = market_map.get(stock['symbol'], {})
        stock['last_price'] = md.get('last_price')
        stock['open_price'] = md.get('open_price')
        stock['high_price'] = md.get('high_price')
        stock['low_price'] = md.get('low_price')
        stock['prev_close'] = md.get('prev_close')
        stock['volume'] = md.get('volume')
        stock['change_pct'] = md.get('change_pct', 0)

        # Convert prices if target currency differs from stock's native currency
        if cc and target_currency and stock.get('currency'):
            native = stock['currency']
            if native != target_currency:
                for field in ['last_price', 'open_price', 'high_price', 'low_price', 'prev_close']:
                    if stock.get(field) is not None:
                        stock[field] = round(cc.convert(stock[field], native, target_currency), 4)
                if stock.get('market_cap'):
                    stock['market_cap'] = int(cc.convert(stock['market_cap'], native, target_currency))
                stock['display_currency'] = target_currency
            else:
                stock['display_currency'] = native
        else:
            stock['display_currency'] = stock.get('currency', 'USD')

    indices = database.get_all_indices()
    exchanges = database.get_all_exchanges()
    sectors = database.get_all_sectors()

    return jsonify({
        'stocks': stocks,
        'indices': indices,
        'exchanges': exchanges,
        'sectors': sectors,
        'total': database.get_stock_universe_count(),
        'currency': target_currency or 'USD'
    }), 200


@app.route('/api/stocks/search', methods=['GET'])
def search_stocks_api():
    """Quick search stocks by symbol or name."""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)
    results = database.search_stock_universe(query, limit=limit)
    return jsonify({'results': results}), 200


@app.route('/api/stocks/<symbol>/details', methods=['GET'])
def get_stock_details(symbol):
    """Get detailed stock information."""
    stock_info = database.get_stock_from_universe(symbol)
    if not stock_info:
        return error_response("Stock not found.", 404)

    market_data = database.get_market_data(symbol) or {}
    fundamentals = database.get_fundamentals(symbol) or {}

    return jsonify({
        'info': stock_info,
        'market_data': market_data,
        'fundamentals': fundamentals
    }), 200


@app.route('/api/market/indices', methods=['GET'])
def get_market_indices():
    """Get major market indices."""
    indices = database.get_all_indices()
    return jsonify({'indices': indices}), 200


@app.route('/api/orders', methods=['POST'])
@jwt_required()
def place_order():
    """Place a new order."""
    user_id = int(get_jwt_identity())
    data = request.json

    symbol = data.get('symbol')
    side = data.get('side')
    order_type = data.get('order_type', 'MARKET')
    product_type = data.get('product_type', 'CNC')
    quantity = data.get('quantity')
    price = data.get('price')
    trigger_price = data.get('trigger_price')
    validity = data.get('validity', 'DAY')

    if not symbol or not side or not quantity:
        return error_response("symbol, side, and quantity are required.", 400)

    if side not in ('BUY', 'SELL'):
        return error_response("side must be BUY or SELL.", 400)

    if order_type not in ('MARKET', 'LIMIT', 'SL', 'SL-M'):
        return error_response("Invalid order type.", 400)

    md = database.get_market_data(symbol)
    current_price = md.get('last_price') if md else price

    order_id = database.create_order(
        user_id=user_id, symbol=symbol, side=side,
        order_type=order_type, product_type=product_type,
        quantity=quantity, price=price,
        trigger_price=trigger_price, validity=validity
    )

    # Auto-fill MARKET orders
    if order_type == 'MARKET' and current_price:
        database.fill_order(order_id, current_price)
        try:
            action = 'buy' if side == 'BUY' else 'sell'
            database.add_transaction(user_id, symbol, action, float(quantity), float(current_price))
        except Exception:
            pass

    return jsonify({"status": "success", "order_id": order_id}), 201


@app.route('/api/orders/list', methods=['GET'])
@jwt_required()
def get_orders():
    """Get user's orders."""
    user_id = int(get_jwt_identity())
    status = request.args.get('status')
    orders = database.get_user_orders(user_id, status=status)
    return jsonify({"orders": orders}), 200


@app.route('/api/orders/<int:order_id>/cancel', methods=['DELETE'])
@jwt_required()
def cancel_order_api(order_id):
    """Cancel an open order."""
    user_id = int(get_jwt_identity())
    success = database.cancel_order(order_id, user_id)
    if success:
        return jsonify({"status": "success", "message": "Order cancelled."}), 200
    else:
        return error_response("Order not found or already filled.", 404)


@app.route('/api/positions', methods=['GET'])
@jwt_required()
def get_positions():
    """Get user's current positions with live P&L."""
    user_id = int(get_jwt_identity())
    portfolio = database.get_portfolio(user_id)

    positions = []
    total_pnl = 0

    for item in portfolio:
        symbol = item.get('ticker', item.get('symbol', ''))
        avg_price = float(item.get('avg_price', 0) or 0)
        quantity = float(item.get('quantity', 0) or 0)

        md = database.get_market_data(symbol)
        ltp = float(md.get('last_price', avg_price)) if md else avg_price

        pnl = (ltp - avg_price) * quantity
        pnl_pct = ((ltp - avg_price) / avg_price * 100) if avg_price > 0 else 0
        total_pnl += pnl

        positions.append({
            'symbol': symbol,
            'quantity': quantity,
            'avg_price': round(avg_price, 2),
            'ltp': round(ltp, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'current_value': round(ltp * quantity, 2),
        })

    return jsonify({"positions": positions, "total_pnl": round(total_pnl, 2)}), 200


# ==========================================

# ==========================================
# STATIC SERVING & FALLBACK
# ==========================================
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    # Exclude API routes from static serving to prevent 405/404 masking
    if path.startswith("api/"):
        return jsonify({"status": "error", "message": "API endpoint not found"}), 404
        
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    alert_engine.alert_engine.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
