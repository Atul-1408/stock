import os
import sys
from pathlib import Path
# Fix import path for subpackages
sys.path.append(str(Path(__file__).parent))

import threading
from datetime import timedelta, datetime, timezone
import json
import pandas as pd
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
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

# Validate production configuration and safety constraints
config_validation = Config.validate_production_config()
for warning_msg in config_validation.get("warnings", []):
    app.logger.warning(f"[CONFIG WARNING] {warning_msg}")

# JWT Configuration
app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=Config.JWT_ACCESS_TOKEN_EXPIRES_DAYS)
jwt = JWTManager(app)

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        "status": "error",
        "error": "Token Expired",
        "message": "Your session has expired. Please log in again."
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    return jsonify({
        "status": "error",
        "error": "Invalid Token",
        "message": "Invalid authentication token."
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error_string):
    return jsonify({
        "status": "error",
        "error": "Unauthorized",
        "message": "Authentication token is required."
    }), 401

# CORS Configuration
CORS(
    app,
    resources={r"/api/*": {"origins": Config.CORS_ALLOWED_ORIGINS}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"]
)

@app.after_request
def after_request(response):
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if Config.IS_PRODUCTION:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5000 per day", "500 per hour"],
    storage_uri=Config.RATELIMIT_STORAGE_URI
)

# ==========================================
# HEALTH & OBSERVABILITY PROBES
# ==========================================
@app.route('/api/health', methods=['GET'])
@limiter.exempt
def health_check():
    """System health check endpoint for monitoring and observability."""
    db_ok = False
    db_error = None
    try:
        with database.get_connection() as conn:
            conn.execute("SELECT 1;").fetchone()
            db_ok = True
    except Exception as e:
        db_error = str(e)
        app.logger.error(f"Health check DB probe failed: {e}")

    worker_status = worker_manager.get_health_status()
    overall_status = "healthy" if db_ok else "degraded"

    return jsonify({
        "status": overall_status,
        "environment": Config.ENVIRONMENT,
        "trading_mode": Config.TRADING_MODE,
        "live_trading_enabled": Config.IS_LIVE_TRADING_ENABLED,
        "database": "connected" if db_ok else "unreachable",
        "database_error": db_error,
        "workers": worker_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), (200 if db_ok else 503)


@app.route('/api/health/live', methods=['GET'])
@limiter.exempt
def liveness_probe():
    """Liveness probe for orchestrators (Kubernetes / ECS)."""
    return jsonify({"status": "live"}), 200


@app.route('/api/health/ready', methods=['GET'])
@limiter.exempt
def readiness_probe():
    """Readiness probe verifying DB and core infrastructure."""
    try:
        with database.get_connection() as conn:
            conn.execute("SELECT 1;").fetchone()
        return jsonify({"status": "ready"}), 200
    except Exception as e:
        return jsonify({"status": "not_ready", "error": str(e)}), 503

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
# WORKER LIFECYCLE & BACKGROUND SERVICES
# ==========================================
from worker_manager import worker_manager
import order_validator
from order_validator import duplicate_detector, is_price_recent, validate_order_input

# Start background workers if appropriate (handles single-instance leader locking)
if os.getenv("FLASK_ENV") != "testing" and os.getenv("ENABLE_BACKGROUND_WORKERS", "true").lower() == "true":
    try:
        worker_manager.start_all(app)
    except Exception as e:
        app.logger.warning(f"Background worker startup skipped/deferred: {e}")

class _BotThreadCompat:
    def is_alive(self):
        return worker_manager.is_running("trading_bot")

bot_thread = _BotThreadCompat()

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
    hw = worker_manager.get_health_status()
    return jsonify({
        "status": "ok",
        "service": "stock-sentiment-api",
        "bot_active": worker_manager.is_running("trading_bot"),
        "worker_leader": hw.get("is_leader", False),
        "workers": hw.get("workers", {})
    }), 200


@app.route("/api/workers/health", methods=["GET"])
def workers_health():
    """Detailed health check for all background workers."""
    return jsonify(worker_manager.get_health_status()), 200


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================
@app.route('/api/auth/signup', methods=['POST'])
@limiter.limit("5 per hour")
def signup():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    username = (data.get('username') or '').strip()
    full_name = (data.get('full_name') or '').strip()

    if not email or not password:
        return error_response("Email and password are required.", 400)

    if len(password) < 8:
        return error_response("Password must be at least 8 characters long.", 400)

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
@limiter.limit("20 per hour; 5 per minute")
def login():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')

    if not email or not password:
        return error_response("Email and password are required.", 400)

    user = database.get_user_by_email(email)
    
    # Timing attack mitigation: always execute check_password_hash even if user not found
    dummy_hash = "scrypt:32768:8:1$dummy$dummydummydummydummydummydummydummydummydummy"

    if not user or user.get('password_hash') in ('__GOOGLE_AUTH__', '__OTP_AUTH__', None, ''):
        check_password_hash(dummy_hash, password)
        return error_response("Invalid email or password.", 401)

    if not check_password_hash(user['password_hash'], password):
        return error_response("Invalid email or password.", 401)

    access_token = create_access_token(identity=str(user['id']))
    return jsonify({"status": "success", "access_token": access_token, "user_id": user['id']}), 200

# ---- OTP Login Routes ----
@app.route('/api/auth/otp/send', methods=['POST'])
@limiter.limit("5 per minute")
def send_otp():
    import otp_service
    from datetime import timezone
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return error_response("Email is required.", 400)

    code = otp_service.generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    database.save_otp(email, code, expires_at)

    sent = otp_service.send_otp_email(email, code)
    if sent:
        return jsonify({"status": "success", "message": "OTP sent to your email."}), 200
    else:
        return error_response("Failed to send OTP. Please try again.", 500)

@app.route('/api/auth/otp/verify', methods=['POST'])
@limiter.limit("10 per minute")
def verify_otp_route():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    otp = (data.get('otp') or '').strip()

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

    data = request.json or {}
    credential = data.get('credential')
    if not credential:
        return error_response("Google credential is required.", 400)

    if not Config.GOOGLE_CLIENT_ID:
        return error_response("Google authentication is not configured on this server.", 503)

    try:
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), Config.GOOGLE_CLIENT_ID)
        
        # Verify issuer and email verification status
        if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            return error_response("Invalid Google token issuer.", 401)
        
        if not idinfo.get('email_verified', False):
            return error_response("Google account email is not verified.", 401)

        google_email = (idinfo.get('email') or '').strip().lower()
        google_name = idinfo.get('name', '')

        if not google_email:
            return error_response("Could not get email from Google.", 400)

        user = database.create_or_get_google_user(google_email, google_name)
        if not user:
            return error_response("Failed to create or find user account.", 500)

        access_token = create_access_token(identity=str(user['id']))
        return jsonify({"status": "success", "access_token": access_token, "user_id": user['id']}), 200
    except ValueError:
        return error_response("Invalid Google token.", 401)
    except Exception as e:
        app.logger.error(f"Google auth error: {e}")
        return error_response("Failed to authenticate with Google.", 401)

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
    
    trades = database.get_bot_trades(user_id)
    return jsonify({'trades': trades}), 200

@app.route('/api/bot/performance', methods=['GET'])
@jwt_required()
def get_bot_performance():
    """Get bot performance metrics"""
    user_id = int(get_jwt_identity())
    
    trades = database.get_closed_bot_trades(user_id)
    
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
    winning_trades = len([t for t in trades if (t.get('pnl') or 0) > 0])
    losing_trades = total_trades - winning_trades
    
    total_pnl = sum((t.get('pnl') or 0) for t in trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    profits = [(t.get('pnl') or 0) for t in trades if (t.get('pnl') or 0) > 0]
    losses = [(t.get('pnl') or 0) for t in trades if (t.get('pnl') or 0) < 0]
    
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
    
    try:
        shares_val = float(shares)
    except (ValueError, TypeError):
        return error_response("Shares must be a valid number.", 400)

    clean_ticker = str(ticker).strip().upper()
    clean_action = str(action).strip().upper()

    # Prevent rapid duplicate submissions
    if duplicate_detector.is_duplicate(user_id, clean_ticker, clean_action, shares_val, None):
        return error_response("Duplicate order detected. Please wait a moment before resubmitting.", 409)

    result = trading_engine.execute_trade(user_id, clean_ticker, clean_action, shares_val, sentiment_score, sentiment_label)
    
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
    """Return the last 30 days of sentiment data for a ticker with live caching."""
    ticker = ticker.upper()
    data = database.get_sentiments_last_30_days(ticker)
    if data:
        return jsonify({"status": "success", "data": data}), 200

    # Live processing with normalization, deduplication, and database caching
    try:
        from news_service import process_and_analyze_news
        live_data = process_and_analyze_news(ticker, limit=15)
        return jsonify({"status": "success", "data": live_data}), 200
    except Exception as e:
        app.logger.warning(f"Sentiment live processing error for {ticker}: {e}")
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
                if data:
                    database.insert_prices(ticker, data)
        except Exception as e:
            app.logger.warning(f"Price fetch error for {ticker}: {e}")
    return jsonify({"status": "success", "data": data}), 200

@app.route('/api/news/<ticker>', methods=['GET'])
@jwt_required()
@limiter.limit("60 per minute")
def get_news_for_ticker(ticker):
    """Return recent news with normalized sentiment, confidence, and deduplication for a ticker."""
    ticker = ticker.upper()
    try:
        from news_service import process_and_analyze_news
        data = process_and_analyze_news(ticker, limit=15)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as e:
        app.logger.warning(f"News fetch error for {ticker}: {e}")
        # Graceful fallback to existing DB records
        cached = database.get_news_with_latest_sentiment(ticker) or []
        return jsonify({"status": "success", "data": cached}), 200

@app.route('/api/market/brief', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_market_brief():
    """Return structured AI Market Brief with verified facts, interpretation, and influential news."""
    try:
        from market_brief_service import generate_market_brief
        brief = generate_market_brief()
        return jsonify(brief), 200
    except Exception as e:
        app.logger.warning(f"Market brief generation error: {e}")
        return jsonify({
            "status": "error",
            "message": "Market brief generation temporarily unavailable.",
            "data": None
        }), 500

@app.route('/api/stocks/<symbol>/intelligence', methods=['GET'])
@jwt_required()
@limiter.limit("60 per minute")
def get_stock_intelligence_api(symbol):
    """Return concise stock intelligence, price dynamics, and news sentiment with limitations."""
    try:
        from stock_intelligence_service import get_stock_intelligence
        intel = get_stock_intelligence(symbol)
        return jsonify(intel), 200
    except Exception as e:
        app.logger.warning(f"Stock intelligence error for {symbol}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Unable to generate intelligence report for {symbol}."
        }), 500

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
    current_user_id = int(get_jwt_identity())
    user = database.get_user_by_id(user_id)
    if not user:
        return error_response("User not found", 404)
    if user_id != current_user_id and not user.get('is_public', 1):
        return error_response("This profile is private.", 403)
    
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
@jwt_required()
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
    try:
        from stock_intelligence_service import get_stock_intelligence
        intel = get_stock_intelligence(ticker.upper())
        analysis = (
            f"### {intel['ticker']} Intelligence Report\n\n"
            f"- **Price:** ${intel['price_metrics']['current_price']:.2f} ({intel['price_metrics']['trend']})\n"
            f"- **Sentiment:** {intel['sentiment_metrics']['label']} (Score: {intel['sentiment_metrics']['score']:+.2f}, N={intel['sentiment_metrics']['sample_size']} headlines)\n"
            f"- **Data Sufficiency:** {'Robust' if intel['sentiment_metrics']['is_sufficient_data'] else 'Limited Sample Size'}\n\n"
            f"**Summary:** {intel['summary']}\n\n"
            f"*{intel['limitations']}*"
        )
        return jsonify({'analysis': analysis, 'intelligence': intel}), 200
    except Exception:
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
@jwt_required()
def get_social_feed_api():
    trades = leaderboard_engine.get_social_feed()
    return jsonify({'trades': trades}), 200

@app.route('/api/social/trades/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_trades_api(user_id):
    current_user_id = int(get_jwt_identity())
    if user_id != current_user_id:
        target = database.get_user_by_id(user_id)
        if not target or not target.get('is_public', 1):
            return error_response("This user's trades are private.", 403)
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
    """Place a new order with balance and position authorization."""
    user_id = int(get_jwt_identity())
    data = request.json or {}

    is_valid, err_msg, sanitized = validate_order_input(data)
    if not is_valid:
        return error_response(err_msg, 400)

    symbol = sanitized['symbol']
    side = sanitized['side']
    order_type = sanitized['order_type']
    product_type = sanitized['product_type']
    qty = sanitized['quantity']
    limit_price = sanitized['price']
    trigger_price = sanitized['trigger_price']
    validity = sanitized['validity']

    # Prevent rapid duplicate submissions
    if duplicate_detector.is_duplicate(user_id, symbol, side, qty, limit_price):
        return error_response("Duplicate order detected. Please wait a moment before resubmitting.", 409)

    # Determine reference price for execution/validation
    md = database.get_market_data(symbol)
    market_price = float(md.get('last_price')) if (md and md.get('last_price')) else None
    if not market_price or market_price <= 0:
        market_price = trading_engine.get_current_price(symbol)

    validation_price = market_price if order_type == 'MARKET' else (limit_price or market_price)
    if not validation_price or validation_price <= 0:
        return error_response(f"Could not determine valid price for {symbol}.", 400)

    # Auto-fill MARKET orders atomically
    if order_type == 'MARKET':
        result = database.execute_trade_atomic(
            user_id=user_id,
            symbol=symbol,
            side=side,
            quantity=qty,
            execution_price=market_price,
            order_type=order_type,
            product_type=product_type
        )
        if not result.get("success"):
            return error_response(result.get("message", "Order execution failed."), 400)

        return jsonify({
            "status": "success",
            "order_id": result["order_id"],
            "data": result
        }), 201

    # Handle pending non-market orders (LIMIT / SL / SL-M)
    user_balance = database.get_user_balance(user_id) or 0.0
    if side == 'BUY':
        total_required = qty * validation_price
        if user_balance < total_required:
            return error_response(
                f"Insufficient funds. Required: ${total_required:,.2f}, Available: ${user_balance:,.2f}", 400
            )
    elif side == 'SELL':
        owned_shares = database.get_user_shares(user_id, symbol)
        if owned_shares < qty:
            return error_response(
                f"Insufficient shares. You only own {owned_shares} shares of {symbol}.", 400
            )

    order_id = database.create_order(
        user_id=user_id, symbol=symbol, side=side,
        order_type=order_type, product_type=product_type,
        quantity=qty, price=limit_price,
        trigger_price=trigger_price, validity=validity
    )

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
        avg_price = float(item.get('avg_buy_price', item.get('avg_price', 0)) or 0)
        quantity = float(item.get('shares', item.get('quantity', 0)) or 0)

        md = database.get_market_data(symbol)
        ltp = float(md.get('last_price')) if (md and md.get('last_price')) else None
        if not ltp or ltp <= 0:
            ltp = trading_engine.get_current_price(symbol)
        if not ltp or ltp <= 0:
            ltp = avg_price

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
    worker_manager.start_all(app)
    app.run(host="0.0.0.0", port=5000, debug=False)
