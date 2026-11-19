"""Database utilities for the Stock Sentiment Analysis Dashboard.

Creates SQLite tables and provides helper functions to store/query data.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config


logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with dict-like row access and hardened concurrency settings."""
    db_file = Path(Config.DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_file, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA busy_timeout = 5000;")
    connection.execute("PRAGMA synchronous = NORMAL;")
    return connection


def init_db() -> None:
    """Create all required tables if they do not already exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                username TEXT,
                full_name TEXT,
                starting_balance REAL DEFAULT 100000.00,
                current_balance REAL DEFAULT 100000.00,
                bio TEXT,
                avatar_url TEXT,
                is_public INTEGER DEFAULT 1, -- 1 for True, 0 for False
                twitter_handle TEXT,
                role TEXT DEFAULT 'user',
                created_at TEXT NOT NULL
            )
            """
        )

        # Alerts
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                alert_type TEXT NOT NULL, -- 'sentiment_drop', 'sentiment_rise', 'price_target', 'news_alert'
                condition_operator TEXT,   -- 'below', 'above', 'equals'
                threshold_value REAL,
                is_active INTEGER DEFAULT 1,
                notification_method TEXT DEFAULT 'email', -- 'email', 'telegram', 'both'
                created_at TEXT NOT NULL,
                last_triggered TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_rule_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                alert_type TEXT,
                message TEXT,
                sentiment_score REAL,
                price REAL,
                triggered_at TEXT NOT NULL,
                was_read INTEGER DEFAULT 0,
                FOREIGN KEY(alert_rule_id) REFERENCES alert_rules(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Social
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                following_id INTEGER NOT NULL,
                followed_at TEXT NOT NULL,
                UNIQUE(follower_id, following_id),
                FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(following_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shared_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT, -- 'BUY' or 'SELL'
                entry_price REAL,
                target_price REAL,
                sentiment_score REAL,
                reasoning TEXT,
                is_public INTEGER DEFAULT 1,
                likes_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shared_trade_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                comment_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(shared_trade_id) REFERENCES shared_trades(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shared_trade_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(shared_trade_id, user_id),
                FOREIGN KEY(shared_trade_id) REFERENCES shared_trades(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Chat System
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL, -- 'user' or 'assistant'
                content TEXT NOT NULL,
                stocks_mentioned TEXT, -- JSON string of tickers
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE
            )
            """
        )

        # Migration: Add columns to users if they don't exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT")
        except: pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
        except: pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_public INTEGER DEFAULT 1")
        except: pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN twitter_handle TEXT")
        except: pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except: pass

        # Token blocklist table for JWT revocation
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS token_blocklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jti TEXT UNIQUE NOT NULL,
                token_type TEXT NOT NULL,
                user_id INTEGER,
                revoked_at TEXT NOT NULL
            )
            """
        )

        # Portfolio holdings
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                shares REAL NOT NULL,
                avg_buy_price REAL NOT NULL,
                total_invested REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, ticker),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Transaction history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL, -- 'BUY' or 'SELL'
                shares REAL NOT NULL,
                price_per_share REAL NOT NULL,
                total_value REAL NOT NULL,
                sentiment_score REAL,
                sentiment_label TEXT,
                commission REAL DEFAULT 0.00,
                is_bot INTEGER DEFAULT 0,
                realized_pnl REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL,
                notes TEXT,
                currency TEXT DEFAULT 'USD',
                base_currency TEXT DEFAULT 'USD',
                base_price_per_share REAL,
                base_total_value REAL,
                exchange_rate REAL DEFAULT 1.0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Watchlists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                added_at TEXT NOT NULL,
                UNIQUE(user_id, ticker),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Articles and sentiment (Legacy support for global news)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT UNIQUE,
                source TEXT,
                published_at TEXT,
                fetched_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sentiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                model_name TEXT,
                sentiment_label TEXT,
                sentiment_score REAL,
                analyzed_at TEXT NOT NULL,
                FOREIGN KEY(article_id) REFERENCES articles(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                fetched_at TEXT NOT NULL,
                UNIQUE(ticker, trade_date)
            )
            """
        )

        # OTP Codes table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS otp_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                salt TEXT NOT NULL DEFAULT '',
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0
            )
            """
        )

        # ==========================================
        # BROKER-STYLE TABLES
        # ==========================================

        # Stock Universe — master listing of all tradable stocks
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_universe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                exchange TEXT NOT NULL,
                sector TEXT,
                industry TEXT,
                market_cap INTEGER,
                country TEXT,
                currency TEXT DEFAULT 'USD',
                is_active INTEGER DEFAULT 1,
                last_updated TEXT
            )
            """
        )

        # Market data cache — real-time price data
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_data_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                last_price REAL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                prev_close REAL,
                volume INTEGER,
                change_pct REAL,
                last_trade_time TEXT,
                updated_at TEXT
            )
            """
        )

        # Stock fundamentals
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_fundamentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                pe_ratio REAL,
                pb_ratio REAL,
                dividend_yield REAL,
                eps REAL,
                book_value REAL,
                face_value REAL,
                fifty_two_week_high REAL,
                fifty_two_week_low REAL,
                avg_volume_30d INTEGER,
                shares_outstanding INTEGER,
                updated_at TEXT
            )
            """
        )

        # Market indices
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_indices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                current_value REAL,
                open_value REAL,
                high_value REAL,
                low_value REAL,
                prev_close REAL,
                change_pct REAL,
                updated_at TEXT
            )
            """
        )

        # Orders table (advanced order types)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL DEFAULT 'MARKET',
                product_type TEXT NOT NULL DEFAULT 'CNC',
                quantity REAL NOT NULL,
                price REAL,
                trigger_price REAL,
                validity TEXT DEFAULT 'DAY',
                status TEXT DEFAULT 'OPEN',
                filled_quantity REAL DEFAULT 0,
                filled_price REAL,
                is_bot INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # ==========================================
        # CURRENCY SYSTEM TABLES
        # ==========================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS currencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                country_code TEXT,
                is_active INTEGER DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate REAL NOT NULL,
                updated_at TEXT,
                UNIQUE(from_currency, to_currency)
            )
            """
        )

        # Migration: add preferred_currency to users if not exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN preferred_currency TEXT DEFAULT 'USD'")
        except Exception:
            pass  # Column already exists

        # Seed currencies
        default_currencies = [
            ('USD', 'US Dollar', '$', 'US'),
            ('INR', 'Indian Rupee', 'Rs.', 'IN'),
            ('EUR', 'Euro', '€', 'EU'),
            ('GBP', 'British Pound', '£', 'GB'),
            ('JPY', 'Japanese Yen', '¥', 'JP'),
            ('AUD', 'Australian Dollar', 'A$', 'AU'),
            ('CAD', 'Canadian Dollar', 'C$', 'CA'),
            ('CHF', 'Swiss Franc', 'CHF', 'CH'),
            ('CNY', 'Chinese Yuan', '¥', 'CN'),
            ('SGD', 'Singapore Dollar', 'S$', 'SG'),
            ('HKD', 'Hong Kong Dollar', 'HK$', 'HK'),
            ('AED', 'UAE Dirham', 'AED', 'AE'),
            ('BRL', 'Brazilian Real', 'R$', 'BR'),
            ('MXN', 'Mexican Peso', 'MX$', 'MX'),
            ('ZAR', 'South African Rand', 'R', 'ZA'),
        ]
        for code, name, symbol, cc in default_currencies:
            try:
                cursor.execute("INSERT INTO currencies (code, name, symbol, country_code) VALUES (?, ?, ?, ?)", (code, name, symbol, cc))
            except Exception:
                pass

        # Seed base exchange rates (USD as base)
        default_rates = [
            ('USD', 'USD', 1.0), ('USD', 'INR', 83.20), ('USD', 'EUR', 0.92),
            ('USD', 'GBP', 0.79), ('USD', 'JPY', 149.50), ('USD', 'AUD', 1.52),
            ('USD', 'CAD', 1.36), ('USD', 'CHF', 0.88), ('USD', 'CNY', 7.24),
            ('USD', 'SGD', 1.34), ('USD', 'HKD', 7.82), ('USD', 'AED', 3.67),
            ('USD', 'BRL', 4.97), ('USD', 'MXN', 17.15), ('USD', 'ZAR', 18.65),
        ]
        for fc, tc, rate in default_rates:
            try:
                cursor.execute("INSERT INTO exchange_rates (from_currency, to_currency, rate, updated_at) VALUES (?, ?, ?, ?)",
                               (fc, tc, rate, datetime.now(timezone.utc).isoformat()))
            except Exception:
                pass

        # Migration: Allow password_hash to be NULL (for Google OAuth users)
        # SQLite doesn't support ALTER COLUMN, so we handle this at insert time
        # by not enforcing NOT NULL on password_hash for new Google users.

        # Phase 5: AI Intelligence Schema Migrations
        try:
            cursor.execute("ALTER TABLE articles ADD COLUMN processing_status TEXT DEFAULT 'analyzed'")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE sentiments ADD COLUMN confidence REAL")
        except Exception:
            pass

        # Phase D: Unified Ledger Migrations
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN is_bot INTEGER DEFAULT 0")
        except Exception:
            pass
        for col_def in [
            "currency TEXT DEFAULT 'USD'",
            "base_currency TEXT DEFAULT 'USD'",
            "base_price_per_share REAL",
            "base_total_value REAL",
            "exchange_rate REAL DEFAULT 1.0"
        ]:
            try:
                cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col_def}")
            except Exception:
                pass
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN realized_pnl REAL DEFAULT 0.0")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN is_bot INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE otp_codes ADD COLUMN salt TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE otp_codes ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        # Bot System
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 0,
                max_position_size REAL DEFAULT 1000.0,
                risk_level TEXT DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH'
                use_sentiment INTEGER DEFAULT 1,
                min_sentiment_score REAL DEFAULT 0.2,
                use_technical INTEGER DEFAULT 1,
                use_ml_model INTEGER DEFAULT 0,
                stop_loss_pct REAL DEFAULT 0.05,
                take_profit_pct REAL DEFAULT 0.1,
                max_trades_per_day INTEGER DEFAULT 5,
                trading_hours_start TEXT DEFAULT '09:00:00',
                trading_hours_end TEXT DEFAULT '16:00:00',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                added_at TEXT NOT NULL,
                UNIQUE(user_id, ticker),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL, -- 'BUY' or 'SELL'
                shares INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                sentiment_at_entry REAL,
                technical_score REAL,
                ml_score REAL,
                status TEXT DEFAULT 'OPEN', -- 'OPEN', 'CLOSED'
                entry_time TEXT NOT NULL,
                exit_price REAL,
                pnl REAL,
                pnl_pct REAL,
                exit_time TEXT,
                exit_reason TEXT, -- 'STOP_LOSS', 'TAKE_PROFIT', 'MANUAL', 'SIGNAL'
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL,
                sentiment_score REAL,
                technical_score REAL,
                ml_score REAL,
                price REAL,
                reasoning TEXT,
                was_executed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Performance Indexes (must come AFTER all table definitions)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_ticker ON transactions(user_id, ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_ticker ON portfolio(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user_ticker ON portfolio(user_id, ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_conversations_user ON chat_conversations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_otp_codes_email ON otp_codes(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_otp_codes_email_used ON otp_codes(email, used)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_universe_symbol ON stock_universe(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_universe_exchange ON stock_universe(exchange)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_universe_sector ON stock_universe(sector)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data_cache(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_rules_user_active ON alert_rules(user_id, is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_logs_user ON alert_logs(user_id, was_read)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON prices(ticker, trade_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shared_trades_user ON shared_trades(user_id, is_public)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchange_rates_pair ON exchange_rates(from_currency, to_currency)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_currency ON users(preferred_currency)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_trades_user ON bot_trades(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_signals_user ON bot_signals(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_watchlist_user ON bot_watchlist(user_id)")

        conn.commit()


def insert_articles(ticker: str, articles: List[Dict]) -> int:
    """Insert article records and return count of inserted rows."""
    inserted = 0
    fetched_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()

        for article in articles:
            try:
                cursor.execute(
                    """
                    INSERT INTO articles (
                        ticker, title, description, url, source, published_at, fetched_at, processing_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticker.upper(),
                        article.get("title", "No title"),
                        article.get("description"),
                        article.get("url"),
                        article.get("source", "Unknown"),
                        article.get("published_at"),
                        fetched_at,
                        article.get("processing_status", "analyzed"),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # Skip duplicates (same URL)
                continue

        conn.commit()

    return inserted


def insert_prices(ticker: str, prices: List[Dict]) -> int:
    """Insert price records and return count of inserted rows."""
    inserted = 0
    fetched_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()

        for row in prices:
            try:
                cursor.execute(
                    """
                    INSERT INTO prices (
                        ticker, trade_date, open, high, low, close, adj_close, volume, fetched_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticker.upper(),
                        row["trade_date"],
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row.get("close"),
                        row.get("adj_close"),
                        row.get("volume"),
                        fetched_at,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # Skip duplicates (same ticker + date)
                continue

        conn.commit()

    return inserted


def get_article_id_by_url(url: Optional[str]) -> Optional[int]:
    """Find article ID by URL. Returns None if not found."""
    if not url:
        return None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
        row = cursor.fetchone()
        return int(row["id"]) if row else None


def get_cached_sentiment_for_url(url: Optional[str]) -> Optional[Dict]:
    """Look up existing sentiment for an article URL to prevent reprocessing."""
    if not url:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                s.sentiment_label,
                s.sentiment_score,
                s.confidence,
                s.model_name,
                s.analyzed_at
            FROM sentiments s
            JOIN articles a ON a.id = s.article_id
            WHERE a.url = ?
            ORDER BY s.analyzed_at DESC LIMIT 1
            """,
            (url,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def insert_sentiment(article_id: int, model_name: str, label: str, score: float, confidence: Optional[float] = None) -> int:
    """Insert one sentiment record with optional confidence. Returns inserted row count (1 or 0)."""
    analyzed_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sentiments (
                article_id, model_name, sentiment_label, sentiment_score, confidence, analyzed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (article_id, model_name, label, score, confidence, analyzed_at),
        )
        conn.commit()
        return cursor.rowcount


def get_prices_last_30_days(ticker: str) -> List[Dict]:
    """Return last 30 calendar days of prices for ticker."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT trade_date, open, high, low, close, adj_close, volume
            FROM prices
            WHERE ticker = ?
              AND date(trade_date) >= date('now', '-30 day')
            ORDER BY trade_date DESC
            """,
            (ticker.upper(),),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_news_with_latest_sentiment(ticker: str) -> List[Dict]:
    """Return recent news for ticker with latest linked sentiment if available."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.ticker,
                a.title,
                a.description,
                a.url,
                a.source,
                a.published_at,
                a.processing_status,
                s.sentiment_label,
                s.sentiment_score,
                s.confidence,
                s.model_name,
                s.analyzed_at
            FROM articles a
            LEFT JOIN sentiments s
              ON s.id = (
                    SELECT s2.id
                    FROM sentiments s2
                    WHERE s2.article_id = a.id
                    ORDER BY s2.analyzed_at DESC
                    LIMIT 1
              )
            WHERE a.ticker = ?
              AND date(COALESCE(a.published_at, a.fetched_at)) >= date('now', '-30 day')
            ORDER BY COALESCE(a.published_at, a.fetched_at) DESC
            """,
            (ticker.upper(),),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_sentiments_last_30_days(ticker: str) -> List[Dict]:
    """Return sentiment entries for ticker in the last 30 days."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.ticker,
                a.title,
                a.url,
                a.source,
                a.published_at,
                a.processing_status,
                s.sentiment_label,
                s.sentiment_score,
                s.confidence,
                s.model_name,
                s.analyzed_at
            FROM sentiments s
            JOIN articles a ON a.id = s.article_id
            WHERE a.ticker = ?
              AND date(COALESCE(a.published_at, s.analyzed_at)) >= date('now', '-30 day')
            ORDER BY s.analyzed_at DESC
            """,
            (ticker.upper(),),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# --- OTP Helpers ---
def _otp_digest(code: str, salt: str) -> str:
    """Hash OTP code with per-row salt using sha256."""
    import hashlib
    return hashlib.sha256((str(code) + str(salt)).encode('utf-8')).hexdigest()


def save_otp(email: str, code: str, expires_at: str) -> None:
    """Save a salted hash of an OTP code to the database."""
    import secrets
    created_at = datetime.now(timezone.utc).isoformat()
    salt = secrets.token_hex(16)
    code_hash = _otp_digest(code, salt)
    with get_connection() as conn:
        cursor = conn.cursor()
        # Invalidate any previous unused OTPs for this email
        cursor.execute("UPDATE otp_codes SET used = 1 WHERE email = ? AND used = 0", (email.lower(),))
        cursor.execute(
            "INSERT INTO otp_codes (email, code, salt, attempts, created_at, expires_at) VALUES (?, ?, ?, 0, ?, ?)",
            (email.lower(), code_hash, salt, created_at, expires_at)
        )
        conn.commit()


def verify_otp(email: str, code: str) -> bool:
    """Verify an OTP code with sha256(code + salt) and hmac.compare_digest.
    Increments attempts on failure and locks OTP after 5 wrong tries.
    Deletes expired rows.
    """
    import hmac
    delete_expired_otps()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, code, salt, attempts FROM otp_codes
            WHERE email = ? AND used = 0 AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (email.lower(), now)
        )
        row = cursor.fetchone()
        if not row:
            return False

        # Locked after 5 wrong attempts
        if row['attempts'] >= 5:
            return False

        salt = row['salt'] or ''
        expected_hash = _otp_digest(code, salt)
        if hmac.compare_digest(row['code'], expected_hash):
            cursor.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (row['id'],))
            conn.commit()
            return True
        else:
            cursor.execute("UPDATE otp_codes SET attempts = attempts + 1 WHERE id = ?", (row['id'],))
            conn.commit()
            return False


def delete_expired_otps() -> int:
    """Delete expired OTP rows."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM otp_codes WHERE expires_at <= ?", (now,))
        conn.commit()
        return cursor.rowcount


# --- User Management ---
def create_user(email, password_hash, username=None, full_name=None) -> Optional[int]:
    """Create a new user and return user_id."""
    created_at = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, username, full_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email.lower(), password_hash, username, full_name, created_at)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None

def create_or_get_google_user(email: str, full_name: str = None) -> Optional[Dict]:
    """Find or create a user from Google OAuth. Returns user dict."""
    user = get_user_by_email(email)
    if user:
        return user
    # Create a new user without a password (Google-only)
    created_at = datetime.now(timezone.utc).isoformat()
    username = email.split('@')[0]
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, username, full_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email.lower(), '__GOOGLE_AUTH__', username, full_name, created_at)
            )
            conn.commit()
            return get_user_by_id(cursor.lastrowid)
    except sqlite3.IntegrityError:
        return get_user_by_email(email)

def get_user_by_email(email: str) -> Optional[Dict]:
    """Fetch user by email."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Fetch user by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_role(user_id: int) -> str:
    """Get a user's role ('user' or 'admin'). Defaults to 'user'."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return (row['role'] if row and row['role'] else 'user')


def set_user_role(user_id: int, role: str) -> bool:
    """Update a user's role ('user' or 'admin')."""
    if role not in ('user', 'admin'):
        raise ValueError("Role must be 'user' or 'admin'")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
        return cursor.rowcount > 0


def revoke_token(jti: str, token_type: str, user_id: int = None) -> None:
    """Add a JWT JTI to the token blocklist."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO token_blocklist (jti, token_type, user_id, revoked_at) VALUES (?, ?, ?, ?)",
                (jti, token_type, user_id, now)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error revoking token: {e}")


def is_token_revoked(jti: str) -> bool:
    """Check if a JWT JTI exists in the token blocklist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM token_blocklist WHERE jti = ?", (jti,))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking revoked token: {e}")
        return False

def get_all_users() -> List[Dict]:
    """Fetch all users for things like leaderboards."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def update_user_profile(user_id: int, bio: str, avatar_url: str, is_public: bool, twitter_handle: str):
    """Update user profile details."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users 
            SET bio = ?, avatar_url = ?, is_public = ?, twitter_handle = ?
            WHERE id = ?
            """,
            (bio, avatar_url, 1 if is_public else 0, twitter_handle, user_id)
        )
        conn.commit()

def get_user_balance(user_id: int) -> float:
    """Fetch user's current cash balance."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT current_balance FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return float(row["current_balance"]) if row else 0.0

def get_starting_balance(user_id: int) -> float:
    """Fetch user's initial deposit balance."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT starting_balance FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return float(row["starting_balance"]) if row else 0.0

def update_user_balance(user_id: int, new_balance: float):
    """Update user's current cash balance."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET current_balance = ? WHERE id = ?", (new_balance, user_id))
        conn.commit()

# --- Multi-User Trading Helpers ---
def get_user_portfolio(user_id: int) -> List[Dict]:
    """Fetch all holdings for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_portfolio(user_id: int) -> List[Dict]:
    """Alias for get_user_portfolio."""
    return get_user_portfolio(user_id)

def get_user_shares(user_id: int, ticker: str) -> float:
    """Get number of shares a user holds for a ticker."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT shares FROM portfolio WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper()))
        row = cursor.fetchone()
        return float(row["shares"]) if row else 0.0

def update_portfolio_item(user_id: int, ticker: str, shares: float, avg_price: float, total_invested: float):
    """Insert or update a portfolio holding."""
    updated_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO portfolio (user_id, ticker, shares, avg_buy_price, total_invested, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, ticker) DO UPDATE SET
                shares = excluded.shares,
                avg_buy_price = excluded.avg_buy_price,
                total_invested = excluded.total_invested,
                updated_at = excluded.updated_at
            """,
            (user_id, ticker.upper(), shares, avg_price, total_invested, updated_at, updated_at)
        )
        conn.commit()

def delete_portfolio_item(user_id: int, ticker: str):
    """Remove a holding (if shares become 0)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper()))
        conn.commit()

def add_transaction(user_id: int, ticker: str, action: str, shares: float, price: float, total_value: float, sentiment_score: Optional[float] = None, sentiment_label: Optional[str] = None):
    """Log a transaction."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (user_id, ticker, action, shares, price_per_share, total_value, sentiment_score, sentiment_label, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, ticker.upper(), action, shares, price, total_value, sentiment_score, sentiment_label, timestamp)
        )
        conn.commit()

def get_transactions_by_user(user_id: int, limit: int = 50) -> List[Dict]:
    """Fetch transaction history for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_transactions_before_date(user_id: int, date: datetime) -> List[Dict]:
    """Fetch all transactions for a user up to a specific date."""
    target_date = date.strftime('%Y-%m-%d %H:%M:%S')
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE user_id = ? AND timestamp <= ? ORDER BY timestamp ASC",
            (user_id, target_date)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_closed_trades(user_id: int, is_bot: Optional[bool] = None) -> List[Dict]:
    """
    Groups Buy/Sell transactions to identify closed trades for P&L analysis
    using the Weighted-Average Cost (WAC) accounting method.
    """
    transactions = get_transactions_by_user(user_id, limit=9999) # Get all
    if is_bot is True:
        transactions = [tx for tx in transactions if tx.get('is_bot') is not None and int(tx.get('is_bot')) == 1]
    elif is_bot is False:
        transactions = [tx for tx in transactions if tx.get('is_bot') is not None and int(tx.get('is_bot')) == 0]

    transactions.reverse() # Chronological order
    
    inventory = {} # ticker -> {'shares': float, 'total_invested': float}
    closed_trades = []
    
    for tx in transactions:
        ticker = tx['ticker']
        action = str(tx['action']).upper()
        shares = float(tx['shares'])
        price = float(tx['price_per_share'])
        total_val = float(tx['total_value'])

        if action == 'BUY':
            if ticker not in inventory:
                inventory[ticker] = {'shares': 0.0, 'total_invested': 0.0}
            inventory[ticker]['shares'] += shares
            inventory[ticker]['total_invested'] += total_val
        elif action == 'SELL':
            # Check if transaction has stored realized_pnl
            stored_pnl = tx.get('realized_pnl')
            if stored_pnl is not None:
                pnl = float(stored_pnl)
                cost_basis = max(0.0, total_val - pnl)
                buy_price = round(cost_basis / shares, 4) if shares > 0 else price
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
            elif ticker in inventory and inventory[ticker]['shares'] > 0:
                inv_shares = inventory[ticker]['shares']
                inv_invested = inventory[ticker]['total_invested']
                avg_buy = inv_invested / inv_shares if inv_shares > 0 else price
                cost_basis = shares * avg_buy
                pnl = total_val - cost_basis
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
                buy_price = avg_buy
                inventory[ticker]['shares'] = max(0.0, inv_shares - shares)
                inventory[ticker]['total_invested'] = max(0.0, inv_invested - cost_basis)
            else:
                buy_price = price
                cost_basis = total_val
                pnl = 0.0
                pnl_pct = 0.0

            raw_bot = tx.get('is_bot')
            closed_trades.append({
                'ticker': ticker,
                'shares': shares,
                'buy_price': round(buy_price, 4),
                'sell_price': price,
                'cost_basis': round(cost_basis, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'timestamp': tx['timestamp'],
                'is_bot': int(raw_bot) if raw_bot is not None else None
            })
                        
    return closed_trades

# --- Alert Helpers ---
def create_alert_rule(user_id, ticker, alert_type, operator, threshold, method):
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alert_rules (user_id, ticker, alert_type, condition_operator, threshold_value, notification_method, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, ticker.upper(), alert_type, operator, threshold, method, timestamp)
        )
        conn.commit()
        return cursor.lastrowid

def get_alert_rules(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_rules WHERE user_id = ?", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_all_active_alerts() -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_rules WHERE is_active = 1")
        return [dict(row) for row in cursor.fetchall()]

def delete_alert_rule(alert_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alert_rules WHERE id = ?", (alert_id,))
        conn.commit()

def toggle_alert_rule(alert_id: int, is_active: bool):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE alert_rules SET is_active = ? WHERE id = ?", (1 if is_active else 0, alert_id))
        conn.commit()

def verify_alert_ownership(alert_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM alert_rules WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        return row and row['user_id'] == user_id

def update_alert_triggered(alert_id: int):
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE alert_rules SET last_triggered = ? WHERE id = ?", (timestamp, alert_id))
        conn.commit()

def add_alert_log(alert_rule_id, user_id, ticker, alert_type, message, sentiment, price):
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alert_logs (alert_rule_id, user_id, ticker, alert_type, message, sentiment_score, price, triggered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (alert_rule_id, user_id, ticker, alert_type, message, sentiment, price, timestamp)
        )
        conn.commit()

def get_alert_logs(user_id, limit=50):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_logs WHERE user_id = ? ORDER BY triggered_at DESC LIMIT ?", (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]

def mark_alert_log_read(log_id, user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE alert_logs SET was_read = 1 WHERE id = ? AND user_id = ?", (log_id, user_id))
        conn.commit()

# --- Bot Alert Helpers ---
def add_bot_alert_log(ticker, message, alert_type="bot_signal", sentiment=None, price=None):
    """Log a bot-generated signal for the global notification system."""
    timestamp = datetime.now(timezone.utc).isoformat()
    # Ensure system user (id 0) and system rule (id 0) exist to satisfy foreign keys
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Ensure System User exists (id 0)
        cursor.execute("SELECT id FROM users WHERE id = 0")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT OR REPLACE INTO users (id, email, password_hash, username, created_at) VALUES (0, 'system@bot.internal', 'SYSTEM', 'Bot Intelligence', ?)",
                (timestamp,)
            )
            
        # 2. Ensure System Alert Rule exists (id 0)
        cursor.execute("SELECT id FROM alert_rules WHERE id = 0")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT OR REPLACE INTO alert_rules (id, user_id, ticker, alert_type, created_at) VALUES (0, 0, 'SYSTEM', 'bot_signal', ?)",
                (timestamp,)
            )
            
        # 3. Log the Bot Alert
        cursor.execute(
            """
            INSERT INTO alert_logs (alert_rule_id, user_id, ticker, alert_type, message, sentiment_score, price, triggered_at)
            VALUES (0, 0, ?, ?, ?, ?, ?, ?)
            """,
            (ticker.upper() if ticker else 'GLOBAL', alert_type, message, sentiment, price, timestamp)
        )
        conn.commit()

def get_bot_alerts(limit=20):
    """Fetch recent bot-generated alerts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM alert_logs WHERE user_id = 0 ORDER BY triggered_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

def clear_bot_alerts():
    """Delete all bot-generated alerts (user_id = 0)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alert_logs WHERE user_id = 0")
        conn.commit()

def shared_trade_visible(trade_id: int, viewer_id: int) -> bool:
    """A shared trade is visible if it is public or belongs to the viewer."""
    with get_connection() as conn:
        row = conn.execute("SELECT user_id, is_public FROM shared_trades WHERE id = ?", (trade_id,)).fetchone()
    return bool(row) and (row['user_id'] == viewer_id or bool(row['is_public']))


def shared_trade_exists(trade_id: int) -> bool:
    with get_connection() as conn:
        return conn.execute("SELECT 1 FROM shared_trades WHERE id = ?", (trade_id,)).fetchone() is not None


# --- Social Helpers ---

def remove_follow(follower_id, following_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_follows WHERE follower_id = ? AND following_id = ?", (follower_id, following_id))
        conn.commit()

def get_follower_count(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM user_follows WHERE following_id = ?", (user_id,))
        return cursor.fetchone()['count']

def get_following_count(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM user_follows WHERE follower_id = ?", (user_id,))
        return cursor.fetchone()['count']

def create_shared_trade(user_id, ticker, action, entry, target, sentiment, reasoning):
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO shared_trades (user_id, ticker, action, entry_price, target_price, sentiment_score, reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, ticker.upper(), action, entry, target, sentiment, reasoning, timestamp)
        )
        conn.commit()
        return cursor.lastrowid

def get_shared_trades_feed(limit=50):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.*, u.username, u.avatar_url 
            FROM shared_trades s
            JOIN users u ON s.user_id = u.id
            WHERE s.is_public = 1
            ORDER BY s.created_at DESC LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_user_shared_trades(user_id, limit=20):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shared_trades WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]

def create_trade_like(trade_id, user_id):
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO trade_likes (shared_trade_id, user_id, created_at) VALUES (?, ?, ?)", (trade_id, user_id, timestamp))
            conn.commit()
    except sqlite3.IntegrityError: pass

def update_likes_count(trade_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE shared_trades SET likes_count = (SELECT COUNT(*) FROM trade_likes WHERE shared_trade_id = ?) WHERE id = ?", (trade_id, trade_id))
        conn.commit()

def create_trade_comment(trade_id, user_id, text):
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO trade_comments (shared_trade_id, user_id, comment_text, created_at) VALUES (?, ?, ?, ?)", (trade_id, user_id, text, timestamp))
        conn.commit()
        return cursor.lastrowid

def update_comments_count(trade_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE shared_trades SET comments_count = (SELECT COUNT(*) FROM trade_comments WHERE shared_trade_id = ?) WHERE id = ?", (trade_id, trade_id))
        conn.commit()

# --- Chat Helpers ---
def create_new_conversation(user_id, title):
    timestamp = datetime.now(timezone.utc).isoformat()
    for attempt in range(2):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO chat_conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (user_id, title, timestamp, timestamp)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.OperationalError as e:
            if attempt == 0 and 'no such table' in str(e).lower():
                init_db()
                continue
            raise

def get_user_conversations(user_id):
    for attempt in range(2):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM chat_conversations WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            if attempt == 0 and 'no such table' in str(e).lower():
                init_db()
                continue
            raise

def verify_conversation_ownership(conversation_id, user_id):
    for attempt in range(2):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM chat_conversations WHERE id = ?", (conversation_id,))
                row = cursor.fetchone()
                return row and row['user_id'] == user_id
        except sqlite3.OperationalError as e:
            if attempt == 0 and 'no such table' in str(e).lower():
                init_db()
                continue
            raise

def save_chat_message(conversation_id, role, content, stocks_mentioned=None):
    timestamp = datetime.now(timezone.utc).isoformat()
    stocks_json = json.dumps(stocks_mentioned) if stocks_mentioned else None
    for attempt in range(2):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO chat_messages (conversation_id, role, content, stocks_mentioned, created_at) VALUES (?, ?, ?, ?, ?)",
                    (conversation_id, role, content, stocks_json, timestamp)
                )
                cursor.execute("UPDATE chat_conversations SET updated_at = ? WHERE id = ?", (timestamp, conversation_id))
                conn.commit()
                return
        except sqlite3.OperationalError as e:
            if attempt == 0 and 'no such table' in str(e).lower():
                init_db()
                continue
            raise

def get_conversation_history(conversation_id, limit=50):
    for attempt in range(2):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, content, stocks_mentioned FROM chat_messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
                    (conversation_id, limit)
                )
                messages = []
                for row in cursor.fetchall():
                    msg = dict(row)
                    if msg.get('stocks_mentioned'):
                        try:
                            msg['stocks_mentioned'] = json.loads(msg['stocks_mentioned'])
                        except Exception:
                            msg['stocks_mentioned'] = []
                    else:
                        msg['stocks_mentioned'] = []
                    messages.append(msg)
                return messages
        except sqlite3.OperationalError as e:
            if attempt == 0 and 'no such table' in str(e).lower():
                init_db()
                continue
            raise


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """Delete one conversation and its messages for a user. Returns True if deleted."""
    for attempt in range(2):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM chat_conversations WHERE id = ? AND user_id = ?",
                    (conversation_id, user_id),
                )
                row = cursor.fetchone()
                if not row:
                    return False

                # Delete messages first (SQLite foreign keys may not be enforced depending on connection).
                cursor.execute(
                    "DELETE FROM chat_messages WHERE conversation_id = ?",
                    (conversation_id,),
                )
                cursor.execute(
                    "DELETE FROM chat_conversations WHERE id = ? AND user_id = ?",
                    (conversation_id, user_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.OperationalError as e:
            if attempt == 0 and 'no such table' in str(e).lower():
                init_db()
                continue
            raise


# ==========================================
# BROKER-STYLE HELPERS
# ==========================================

def bulk_insert_stocks(stocks_data: List[Dict]) -> int:
    """Bulk insert stocks into stock_universe."""
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        for s in stocks_data:
            try:
                cursor.execute(
                    """
                    INSERT INTO stock_universe (symbol, company_name, exchange, sector, industry, market_cap, country, currency, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        company_name = excluded.company_name,
                        sector = excluded.sector,
                        industry = excluded.industry,
                        market_cap = excluded.market_cap,
                        last_updated = excluded.last_updated
                    """,
                    (s.get('symbol'), s.get('company_name', s.get('symbol')), s.get('exchange', 'UNKNOWN'),
                     s.get('sector'), s.get('industry'), s.get('market_cap'),
                     s.get('country', 'USA'), s.get('currency', 'USD'), now)
                )
                inserted += 1
            except Exception:
                continue
        conn.commit()
    return inserted


def search_stock_universe(query: str, exchange: str = 'all', sector: str = 'all', limit: int = 50) -> List[Dict]:
    """Search stocks by symbol or company name with optional filters."""
    with get_connection() as conn:
        cursor = conn.cursor()
        sql = "SELECT * FROM stock_universe WHERE is_active = 1"
        params = []

        if query:
            sql += " AND (symbol LIKE ? OR company_name LIKE ?)"
            q = f"%{query}%"
            params.extend([q, q])

        if exchange and exchange != 'all':
            sql += " AND exchange = ?"
            params.append(exchange)

        if sector and sector != 'all':
            sql += " AND sector = ?"
            params.append(sector)

        sql += " ORDER BY market_cap DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_stock_universe_count() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM stock_universe WHERE is_active = 1")
        return cursor.fetchone()['count']


def get_stock_from_universe(symbol: str) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stock_universe WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_exchanges() -> List[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT exchange FROM stock_universe WHERE is_active = 1 ORDER BY exchange")
        return [row['exchange'] for row in cursor.fetchall()]


def get_all_sectors() -> List[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT sector FROM stock_universe WHERE is_active = 1 AND sector IS NOT NULL ORDER BY sector")
        return [row['sector'] for row in cursor.fetchall()]


# --- Market Data Cache ---
def upsert_market_cache(data: Dict) -> None:
    """Insert or update market data cache for a symbol."""
    now = data.get('updated_at') or datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO market_data_cache (symbol, last_price, open_price, high_price, low_price, prev_close, volume, change_pct, last_trade_time, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                last_price = excluded.last_price,
                open_price = excluded.open_price,
                high_price = excluded.high_price,
                low_price = excluded.low_price,
                prev_close = excluded.prev_close,
                volume = excluded.volume,
                change_pct = excluded.change_pct,
                last_trade_time = excluded.last_trade_time,
                updated_at = excluded.updated_at
            """,
            (data.get('symbol'), data.get('last_price'), data.get('open_price'),
             data.get('high_price'), data.get('low_price'), data.get('prev_close'),
             data.get('volume'), data.get('change_pct'), data.get('last_trade_time'), now)
        )
        conn.commit()


def get_market_data(symbol: str) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM market_data_cache WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_market_data_bulk(symbols: List[str]) -> List[Dict]:
    if not symbols:
        return []
    with get_connection() as conn:
        cursor = conn.cursor()
        placeholders = ','.join(['?' for _ in symbols])
        cursor.execute(f"SELECT * FROM market_data_cache WHERE symbol IN ({placeholders})", symbols)
        return [dict(row) for row in cursor.fetchall()]


# --- Stock Fundamentals ---
def upsert_fundamentals(data: Dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO stock_fundamentals (symbol, pe_ratio, pb_ratio, dividend_yield, eps, book_value, face_value, fifty_two_week_high, fifty_two_week_low, avg_volume_30d, shares_outstanding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                pe_ratio = excluded.pe_ratio, pb_ratio = excluded.pb_ratio, dividend_yield = excluded.dividend_yield,
                eps = excluded.eps, book_value = excluded.book_value, face_value = excluded.face_value,
                fifty_two_week_high = excluded.fifty_two_week_high, fifty_two_week_low = excluded.fifty_two_week_low,
                avg_volume_30d = excluded.avg_volume_30d, shares_outstanding = excluded.shares_outstanding,
                updated_at = excluded.updated_at
            """,
            (data.get('symbol'), data.get('pe_ratio'), data.get('pb_ratio'), data.get('dividend_yield'),
             data.get('eps'), data.get('book_value'), data.get('face_value'),
             data.get('fifty_two_week_high'), data.get('fifty_two_week_low'),
             data.get('avg_volume_30d'), data.get('shares_outstanding'), now)
        )
        conn.commit()


def get_fundamentals(symbol: str) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stock_fundamentals WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None


# --- Market Indices ---
def upsert_index(data: Dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO market_indices (index_name, display_name, current_value, open_value, high_value, low_value, prev_close, change_pct, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(index_name) DO UPDATE SET
                current_value = excluded.current_value, open_value = excluded.open_value,
                high_value = excluded.high_value, low_value = excluded.low_value,
                prev_close = excluded.prev_close, change_pct = excluded.change_pct,
                updated_at = excluded.updated_at
            """,
            (data.get('index_name'), data.get('display_name'), data.get('current_value'),
             data.get('open_value'), data.get('high_value'), data.get('low_value'),
             data.get('prev_close'), data.get('change_pct'), now)
        )
        conn.commit()


def get_all_indices() -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM market_indices ORDER BY index_name")
        return [dict(row) for row in cursor.fetchall()]


# --- Orders & Buying Power System ---

def get_user_reserved_cash(user_id: int) -> float:
    """Calculate total cash reserved by all active pending BUY orders for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(quantity * price), 0.0)
            FROM orders
            WHERE user_id = ? AND side = 'BUY' AND status = 'OPEN'
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0


def get_user_buying_power(user_id: int) -> float:
    """Calculate available cash buying power after deducting active pending BUY order reservations."""
    balance = get_user_balance(user_id) or 0.0
    reserved = get_user_reserved_cash(user_id)
    return max(0.0, round(balance - reserved, 4))


def get_user_reserved_shares(user_id: int, symbol: str) -> float:
    """Calculate total shares reserved by active pending SELL orders for a specific ticker."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(quantity), 0.0)
            FROM orders
            WHERE user_id = ? AND symbol = ? AND side = 'SELL' AND status = 'OPEN'
            """,
            (user_id, symbol.strip().upper())
        )
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0


def get_user_available_shares(user_id: int, symbol: str) -> float:
    """Calculate unreserved shares available to sell for a ticker."""
    total_shares = get_user_shares(user_id, symbol)
    reserved = get_user_reserved_shares(user_id, symbol)
    return max(0.0, round(total_shares - reserved, 6))


def create_order(
    user_id: int,
    symbol: str,
    side: str,
    order_type: str,
    product_type: str,
    quantity: float,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    validity: str = 'DAY',
    is_bot: bool = False
) -> int:
    """
    Creates a pending order while atomically checking and reserving buying power (BUY) or shares (SELL).
    Guarantees:
    - Atomicity via SQLite BEGIN IMMEDIATE write transaction.
    - Prevents concurrent over-reservation of cash across multiple submissions.
    - Raises ValueError if buying power or available shares are insufficient.
    """
    symbol = symbol.strip().upper()
    side = side.strip().upper()
    order_type = order_type.strip().upper()
    product_type = product_type.strip().upper()
    validity = (validity or 'DAY').strip().upper()
    quantity = float(quantity)
    bot_flag = 1 if is_bot else 0
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        # 1. Verify user exists and fetch current cash balance
        cursor.execute("SELECT current_balance FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            conn.rollback()
            raise ValueError(f"User {user_id} does not exist.")
        current_balance = float(user_row['current_balance'])

        # 2. Reservation check under write lock
        if side == 'BUY':
            order_price = float(price) if price is not None and float(price) > 0 else 0.0
            if order_price <= 0 and order_type != 'MARKET':
                conn.rollback()
                raise ValueError("Limit orders must specify a positive price.")

            total_required = round(quantity * order_price, 4)
            cursor.execute(
                """
                SELECT COALESCE(SUM(quantity * price), 0.0)
                FROM orders
                WHERE user_id = ? AND side = 'BUY' AND status = 'OPEN'
                """,
                (user_id,)
            )
            reserved_cash = float(cursor.fetchone()[0])
            available_bp = round(current_balance - reserved_cash, 4)

            if total_required > available_bp:
                conn.rollback()
                raise ValueError(
                    f"Insufficient funds / buying power. Required: ${total_required:,.2f}, Available: ${available_bp:,.2f}"
                )
        elif side == 'SELL':
            cursor.execute("SELECT shares FROM portfolio WHERE user_id = ? AND ticker = ?", (user_id, symbol))
            holding_row = cursor.fetchone()
            owned_shares = float(holding_row['shares']) if holding_row else 0.0

            cursor.execute(
                """
                SELECT COALESCE(SUM(quantity), 0.0)
                FROM orders
                WHERE user_id = ? AND symbol = ? AND side = 'SELL' AND status = 'OPEN'
                """,
                (user_id, symbol)
            )
            reserved_shares = float(cursor.fetchone()[0])
            available_shares = round(owned_shares - reserved_shares, 6)

            if quantity > available_shares:
                conn.rollback()
                raise ValueError(
                    f"Insufficient shares. You only own {owned_shares} shares of {symbol} (available: {available_shares})."
                )
        else:
            conn.rollback()
            raise ValueError(f"Invalid order side: {side}")

        # 3. Insert order
        cursor.execute(
            """
            INSERT INTO orders (user_id, symbol, side, order_type, product_type, quantity, price, trigger_price, validity, status, is_bot, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
            """,
            (user_id, symbol, side, order_type, product_type, quantity, price, trigger_price, validity, bot_flag, now, now)
        )
        order_id = cursor.lastrowid
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_user_orders(user_id: int, status: str = None, limit: int = 50) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM orders WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?", (user_id, status, limit))
        else:
            cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_open_orders(symbol: Optional[str] = None) -> List[Dict]:
    """Retrieve all active orders in OPEN status chronologically."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if symbol:
            cursor.execute(
                "SELECT * FROM orders WHERE status = 'OPEN' AND symbol = ? ORDER BY created_at ASC, id ASC",
                (symbol.strip().upper(),)
            )
        else:
            cursor.execute(
                "SELECT * FROM orders WHERE status = 'OPEN' ORDER BY created_at ASC, id ASC"
            )
        return [dict(row) for row in cursor.fetchall()]


def cancel_order(order_id: int, user_id: Optional[int] = None) -> bool:
    """
    Cancels an active OPEN order atomically under BEGIN IMMEDIATE.
    Instantly releases reserved buying power (BUY) or reserved shares (SELL).
    Returns False if order does not exist or is already FILLED, CANCELLED, or EXPIRED.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        if user_id is not None:
            cursor.execute("SELECT status FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id))
        else:
            cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row or row['status'] != 'OPEN':
            conn.rollback()
            return False

        if user_id is not None:
            cursor.execute(
                "UPDATE orders SET status = 'CANCELLED', updated_at = ? WHERE id = ? AND user_id = ? AND status = 'OPEN'",
                (now, order_id, user_id)
            )
        else:
            cursor.execute(
                "UPDATE orders SET status = 'CANCELLED', updated_at = ? WHERE id = ? AND status = 'OPEN'",
                (now, order_id)
            )
        success = cursor.rowcount > 0
        conn.commit()
        return success
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def expire_order(order_id: int) -> bool:
    """Marks an OPEN order as EXPIRED atomically, releasing any reservation."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row or row['status'] != 'OPEN':
            conn.rollback()
            return False

        cursor.execute(
            "UPDATE orders SET status = 'EXPIRED', updated_at = ? WHERE id = ? AND status = 'OPEN'",
            (now, order_id)
        )
        success = cursor.rowcount > 0
        conn.commit()
        return success
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def expire_stale_orders() -> int:
    """
    Scans for expired DAY/IOC orders and marks them as EXPIRED.
    Releases all buying power reservations for expired orders.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expired_count = 0
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id, validity, created_at FROM orders WHERE status = 'OPEN'")
        open_orders = cursor.fetchall()
        for ord_row in open_orders:
            ord_id = ord_row['id']
            val = (ord_row['validity'] or 'DAY').upper()
            created_at_str = ord_row['created_at']
            should_expire = False
            try:
                created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                if val == 'DAY' and (now.date() > created_dt.date() or (now - created_dt).total_seconds() >= 86400):
                    should_expire = True
                elif val == 'IOC':
                    should_expire = True
            except Exception:
                pass

            if should_expire:
                cursor.execute(
                    "UPDATE orders SET status = 'EXPIRED', updated_at = ? WHERE id = ? AND status = 'OPEN'",
                    (now_iso, ord_id)
                )
                if cursor.rowcount > 0:
                    expired_count += 1
        conn.commit()
        return expired_count
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def fill_order_atomic(order_id: int, execution_price: float) -> Dict:
    """
    Atomically fills an active OPEN order and executes full financial ledger accounting:
    1. Revalidates order status is OPEN under exclusive write lock (duplicate fill & race protection).
    2. Revalidates required cash (BUY) or shares (SELL) at actual execution price.
    3. Debits or credits user cash balance.
    4. Updates portfolio holdings with Weighted-Average Cost (WAC).
    5. Sets orders status = 'FILLED', filled_quantity = quantity, filled_price = execution_price.
    6. Writes an audit transaction into transactions table with realized_pnl and is_bot attribution.
    7. Atomically converts the reservation into a true ledger debit/credit without double-counting.
    """
    import math

    try:
        execution_price = float(execution_price)
    except (ValueError, TypeError):
        return {"success": False, "message": "Execution price must be a positive finite number."}

    if not math.isfinite(execution_price) or math.isnan(execution_price) or math.isinf(execution_price) or execution_price <= 0:
        return {"success": False, "message": "Execution price must be a positive finite number."}

    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        # 1. Fetch order
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            conn.rollback()
            return {"success": False, "message": f"Order {order_id} not found."}

        current_status = order_row['status']
        if current_status != 'OPEN':
            conn.rollback()
            return {
                "success": False,
                "message": f"Order {order_id} cannot be filled because current status is '{current_status}'."
            }

        user_id = order_row['user_id']
        symbol = order_row['symbol'].upper()
        side = order_row['side'].upper()
        order_type = order_row['order_type'].upper()
        quantity = float(order_row['quantity'])
        order_limit_price = float(order_row['price']) if order_row['price'] is not None else None
        is_bot = int(order_row['is_bot'] or 0)

        # 1b. Atomic Limit-Price Enforcement Guard
        if order_type == 'LIMIT' and order_limit_price is not None and order_limit_price > 0:
            if side == 'BUY' and execution_price > order_limit_price:
                conn.rollback()
                return {
                    "success": False,
                    "message": f"Limit price violation: BUY execution price (${execution_price:,.2f}) exceeds limit (${order_limit_price:,.2f})."
                }
            elif side == 'SELL' and execution_price < order_limit_price:
                conn.rollback()
                return {
                    "success": False,
                    "message": f"Limit price violation: SELL execution price (${execution_price:,.2f}) is below limit (${order_limit_price:,.2f})."
                }

        native_total_value = round(quantity * execution_price, 4)
        realized_pnl = 0.0

        # 2. Fetch user balance
        cursor.execute("SELECT current_balance, preferred_currency FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            conn.rollback()
            return {"success": False, "message": f"User {user_id} not found."}
        current_balance = float(user_row['current_balance'])

        # Multi-currency conversion at fill time
        conv = convert_trade_currency(symbol, user_id, execution_price, quantity, conn=conn)
        asset_curr = conv["asset_currency"]
        base_curr = conv["base_currency"]
        rate = conv["exchange_rate"]
        base_price = conv["base_price"]
        base_total = conv["base_total_value"]

        # 3. Fetch portfolio holding
        cursor.execute(
            "SELECT shares, avg_buy_price, total_invested FROM portfolio WHERE user_id = ? AND ticker = ?",
            (user_id, symbol)
        )
        holding_row = cursor.fetchone()
        existing_shares = float(holding_row['shares']) if holding_row else 0.0
        existing_total_invested = float(holding_row['total_invested']) if holding_row else 0.0

        if side == 'BUY':
            if current_balance < base_total:
                # Mark order as REJECTED due to insufficient cash at execution time
                cursor.execute(
                    "UPDATE orders SET status = 'REJECTED', updated_at = ? WHERE id = ? AND status = 'OPEN'",
                    (now, order_id)
                )
                conn.commit()
                return {
                    "success": False,
                    "message": f"Insufficient funds at execution time. Required: {base_total:,.2f} {base_curr}, Available: {current_balance:,.2f} {base_curr}"
                }

            new_balance = round(current_balance - base_total, 4)
            cursor.execute("UPDATE users SET current_balance = ? WHERE id = ?", (new_balance, user_id))

            new_shares = existing_shares + quantity
            new_total_invested = existing_total_invested + base_total
            new_avg_price = round(new_total_invested / new_shares, 4) if new_shares > 0 else base_price

            cursor.execute(
                """
                INSERT INTO portfolio (user_id, ticker, shares, avg_buy_price, total_invested, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, ticker) DO UPDATE SET
                    shares = excluded.shares,
                    avg_buy_price = excluded.avg_buy_price,
                    total_invested = excluded.total_invested,
                    updated_at = excluded.updated_at
                """,
                (user_id, symbol, new_shares, new_avg_price, new_total_invested, now, now)
            )
        elif side == 'SELL':
            if existing_shares < quantity:
                cursor.execute(
                    "UPDATE orders SET status = 'REJECTED', updated_at = ? WHERE id = ? AND status = 'OPEN'",
                    (now, order_id)
                )
                conn.commit()
                return {
                    "success": False,
                    "message": f"Insufficient shares at execution time. Owned: {existing_shares}, Required: {quantity}"
                }

            avg_buy_price = float(holding_row['avg_buy_price']) if holding_row else base_price
            realized_pnl = round((base_price - avg_buy_price) * quantity, 4)
            new_balance = round(current_balance + base_total, 4)
            cursor.execute("UPDATE users SET current_balance = ? WHERE id = ?", (new_balance, user_id))

            new_shares = existing_shares - quantity
            if new_shares <= 0.000001:
                cursor.execute("DELETE FROM portfolio WHERE user_id = ? AND ticker = ?", (user_id, symbol))
                new_shares = 0.0
            else:
                new_total_invested = max(0.0, existing_total_invested - (quantity * avg_buy_price))
                cursor.execute(
                    "UPDATE portfolio SET shares = ?, total_invested = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                    (new_shares, new_total_invested, now, user_id, symbol)
                )
        else:
            conn.rollback()
            return {"success": False, "message": f"Invalid order side '{side}'."}

        # 4. Mark order as FILLED
        cursor.execute(
            """
            UPDATE orders
            SET status = 'FILLED', filled_quantity = quantity, filled_price = ?, updated_at = ?
            WHERE id = ? AND status = 'OPEN'
            """,
            (execution_price, now, order_id)
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return {"success": False, "message": "Concurrent modification: Order is no longer OPEN."}

        # 5. Insert transaction record with multi-currency fields
        cursor.execute(
            """
            INSERT INTO transactions (
                user_id, ticker, action, shares, price_per_share, total_value, is_bot, realized_pnl, timestamp,
                currency, base_currency, base_price_per_share, base_total_value, exchange_rate
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, symbol, side, quantity, execution_price, native_total_value, is_bot, realized_pnl, now,
             asset_curr, base_curr, base_price, base_total, rate)
        )

        conn.commit()

        return {
            "success": True,
            "order_id": order_id,
            "user_id": user_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "filled_price": execution_price,
            "total_value": native_total_value,
            "base_total_value": base_total,
            "currency": asset_curr,
            "base_currency": base_curr,
            "exchange_rate": rate,
            "new_balance": new_balance,
            "remaining_shares": new_shares if side == 'SELL' else (existing_shares + quantity),
            "realized_pnl": realized_pnl,
            "is_bot": bool(is_bot)
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def fill_order(order_id: int, filled_price: float) -> None:
    """Legacy helper: forwards to fill_order_atomic for unified financial ledger safety."""
    result = fill_order_atomic(order_id, filled_price)
    if not result.get("success"):
        logger.warning(f"fill_order failed for order {order_id}: {result.get('message')}")


def get_symbol_currency(symbol: str) -> str:
    """Return the native currency code for a given symbol (INR for .NS/.BO, USD otherwise)."""
    sym = symbol.strip().upper()
    if sym.endswith(".NS") or sym.endswith(".BO"):
        return "INR"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT currency FROM stock_universe WHERE symbol = ?", (sym,))
            row = cur.fetchone()
            if row and row['currency']:
                return str(row['currency']).upper()
    except Exception:
        pass
    return "USD"


def convert_trade_currency(symbol: str, user_id: int, execution_price: float, quantity: float, conn=None) -> Dict[str, Any]:
    """
    # DECISION: Implemented option (b) - converting execution price to user's base currency
    # using currency_converter at fill time and recording both native and base currency amounts in transactions.
    """
    from currency_converter import currency_converter
    asset_curr = get_symbol_currency(symbol)

    user_curr = "USD"
    try:
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT preferred_currency FROM users WHERE id = ?", (user_id,))
            urow = cur.fetchone()
            if urow and urow['preferred_currency']:
                user_curr = str(urow['preferred_currency']).upper()
        else:
            user_curr = get_user_preferred_currency(user_id)
    except Exception:
        user_curr = "USD"

    native_total_value = round(quantity * execution_price, 4)
    if asset_curr == user_curr:
        return {
            "asset_currency": asset_curr,
            "base_currency": user_curr,
            "exchange_rate": 1.0,
            "native_price": execution_price,
            "native_total_value": native_total_value,
            "base_price": execution_price,
            "base_total_value": native_total_value
        }

    converted_price = currency_converter.convert(execution_price, asset_curr, user_curr)
    if converted_price is None or converted_price <= 0:
        base_price = execution_price
        rate = 1.0
    else:
        base_price = round(converted_price, 4)
        rate = round(base_price / execution_price, 6) if execution_price > 0 else 1.0

    base_total_value = round(quantity * base_price, 4)
    return {
        "asset_currency": asset_curr,
        "base_currency": user_curr,
        "exchange_rate": rate,
        "native_price": execution_price,
        "native_total_value": native_total_value,
        "base_price": base_price,
        "base_total_value": base_total_value
    }


def execute_trade_atomic(
    user_id: int,
    symbol: str,
    side: str,
    quantity: float,
    execution_price: float,
    order_type: str = 'MARKET',
    product_type: str = 'CNC',
    sentiment_score: Optional[float] = None,
    sentiment_label: Optional[str] = None,
    is_bot: bool = False
) -> Dict:
    """
    Executes a complete trade within a single atomic database transaction.
    Guarantees consistency across users balance, portfolio holdings, orders, and transaction audit logs.
    Implements Weighted-Average Cost (WAC) accounting and precise realized P&L calculation.
    """
    symbol = symbol.strip().upper()
    side = side.strip().upper()
    quantity = float(quantity)
    execution_price = float(execution_price)
    native_total_value = round(quantity * execution_price, 4)
    total_value = native_total_value
    now = datetime.now(timezone.utc).isoformat()
    bot_flag = 1 if is_bot else 0
    realized_pnl = 0.0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Immediate exclusive write lock for this transaction
        cursor.execute("BEGIN IMMEDIATE")

        # 1. Fetch user balance & preferred currency
        cursor.execute("SELECT current_balance, preferred_currency FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            conn.rollback()
            return {"success": False, "message": "User not found."}
        current_balance = float(user_row['current_balance'])

        # Multi-currency conversion at fill time
        conv = convert_trade_currency(symbol, user_id, execution_price, quantity, conn=conn)
        asset_curr = conv["asset_currency"]
        base_curr = conv["base_currency"]
        rate = conv["exchange_rate"]
        base_price = conv["base_price"]
        base_total = conv["base_total_value"]

        # 2. Fetch current holding
        cursor.execute(
            "SELECT shares, avg_buy_price, total_invested FROM portfolio WHERE user_id = ? AND ticker = ?",
            (user_id, symbol)
        )
        holding_row = cursor.fetchone()
        existing_shares = float(holding_row['shares']) if holding_row else 0.0
        existing_total_invested = float(holding_row['total_invested']) if holding_row else 0.0

        if side == 'BUY':
            if current_balance < base_total:
                conn.rollback()
                return {
                    "success": False,
                    "message": f"Insufficient funds. Required: {base_total:,.2f} {base_curr}, Available: {current_balance:,.2f} {base_curr}"
                }

            new_balance = round(current_balance - base_total, 4)
            cursor.execute("UPDATE users SET current_balance = ? WHERE id = ?", (new_balance, user_id))

            new_shares = existing_shares + quantity
            new_total_invested = existing_total_invested + base_total
            new_avg_price = round(new_total_invested / new_shares, 4) if new_shares > 0 else base_price

            cursor.execute(
                """
                INSERT INTO portfolio (user_id, ticker, shares, avg_buy_price, total_invested, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, ticker) DO UPDATE SET
                    shares = excluded.shares,
                    avg_buy_price = excluded.avg_buy_price,
                    total_invested = excluded.total_invested,
                    updated_at = excluded.updated_at
                """,
                (user_id, symbol, new_shares, new_avg_price, new_total_invested, now, now)
            )
        elif side == 'SELL':
            if existing_shares < quantity:
                conn.rollback()
                return {
                    "success": False,
                    "message": f"Insufficient shares. You only own {existing_shares} shares of {symbol}."
                }

            avg_buy_price = float(holding_row['avg_buy_price']) if holding_row else base_price
            realized_pnl = round((base_price - avg_buy_price) * quantity, 4)

            new_balance = round(current_balance + base_total, 4)
            cursor.execute("UPDATE users SET current_balance = ? WHERE id = ?", (new_balance, user_id))

            new_shares = existing_shares - quantity
            if new_shares <= 0.000001:
                cursor.execute("DELETE FROM portfolio WHERE user_id = ? AND ticker = ?", (user_id, symbol))
                new_shares = 0.0
            else:
                new_total_invested = max(0.0, existing_total_invested - (quantity * avg_buy_price))
                cursor.execute(
                    "UPDATE portfolio SET shares = ?, total_invested = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                    (new_shares, new_total_invested, now, user_id, symbol)
                )
        else:
            conn.rollback()
            return {"success": False, "message": "Invalid side. Must be BUY or SELL."}

        # 3. Create and fill order record
        cursor.execute(
            """
            INSERT INTO orders (user_id, symbol, side, order_type, product_type, quantity, price, trigger_price, validity, status, filled_quantity, filled_price, is_bot, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'DAY', 'FILLED', ?, ?, ?, ?, ?)
            """,
            (user_id, symbol, side, order_type, product_type, quantity, execution_price, quantity, execution_price, bot_flag, now, now)
        )
        order_id = cursor.lastrowid

        # 4. Record transaction in audit log with multi-currency fields
        cursor.execute(
            """
            INSERT INTO transactions (
                user_id, ticker, action, shares, price_per_share, total_value,
                sentiment_score, sentiment_label, is_bot, realized_pnl, timestamp,
                currency, base_currency, base_price_per_share, base_total_value, exchange_rate
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, symbol, side, quantity, execution_price, native_total_value, sentiment_score, sentiment_label, bot_flag, realized_pnl, now,
             asset_curr, base_curr, base_price, base_total, rate)
        )

        conn.commit()

        return {
            "success": True,
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "filled_price": execution_price,
            "total_value": total_value,
            "new_balance": new_balance,
            "remaining_shares": new_shares if side == 'SELL' else (existing_shares + quantity),
            "realized_pnl": realized_pnl,
            "is_bot": bool(is_bot)
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def backup_database(destination_path: Optional[str] = None) -> str:
    """Create an online hot backup of the SQLite database using SQLite backup API."""
    db_file = Path(Config.DB_PATH)
    if not destination_path:
        backup_dir = db_file.parent / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_path = str(backup_dir / f"backup_{timestamp}.db")

    dest_path = Path(destination_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as src_conn:
        dest_conn = sqlite3.connect(str(dest_path))
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()

    return str(dest_path)


# --- Currency Helpers ---
def get_all_currencies() -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, name, symbol, country_code FROM currencies WHERE is_active = 1 ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]


def get_user_preferred_currency(user_id: int) -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT preferred_currency FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row['preferred_currency'] if row and row['preferred_currency'] else 'USD'


def set_user_preferred_currency(user_id: int, currency_code: str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET preferred_currency = ? WHERE id = ?", (currency_code, user_id))
        conn.commit()


# --- Bot System ---

def get_bot_config(user_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bot_configs WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_bot_config(user_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bot_configs (user_id, created_at, updated_at)
            VALUES (?, ?, ?)
            """,
            (user_id, now, now)
        )
        conn.commit()


def update_bot_config(user_id: int, data: Dict) -> bool:
    # DECISION: Enforce stop_loss_pct and take_profit_pct as fractions (0 < x <= 1) and max_trades_per_day between 1 and 100.
    if 'stop_loss_pct' in data:
        sl = float(data['stop_loss_pct'])
        if sl <= 0 or sl > 1.0:
            raise ValueError("stop_loss_pct must be a fraction between 0 and 1")
        data['stop_loss_pct'] = sl

    if 'take_profit_pct' in data:
        tp = float(data['take_profit_pct'])
        if tp <= 0 or tp > 1.0:
            raise ValueError("take_profit_pct must be a fraction between 0 and 1")
        data['take_profit_pct'] = tp

    if 'max_trades_per_day' in data:
        mtd = int(data['max_trades_per_day'])
        if mtd < 1 or mtd > 100:
            raise ValueError("max_trades_per_day must be an integer between 1 and 100")
        data['max_trades_per_day'] = mtd

    now = datetime.now(timezone.utc).isoformat()
    # Fields that can be updated
    fields = [
        'is_active', 'max_position_size', 'risk_level', 'use_sentiment',
        'min_sentiment_score', 'use_technical', 'use_ml_model',
        'stop_loss_pct', 'take_profit_pct', 'max_trades_per_day',
        'trading_hours_start', 'trading_hours_end'
    ]
    
    set_clauses = []
    params = []
    
    for field in fields:
        if field in data:
            set_clauses.append(f"{field} = ?")
            params.append(data[field])
            
    if not set_clauses:
        return False
        
    # Ensure bot config row exists for user
    if not get_bot_config(user_id):
        create_bot_config(user_id)

    set_clauses.append("updated_at = ?")
    params.append(now)
    params.append(user_id)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE bot_configs SET {', '.join(set_clauses)} WHERE user_id = ?",
            params
        )
        conn.commit()
        return cursor.rowcount > 0


def get_bot_watchlist(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bot_watchlist WHERE user_id = ? ORDER BY ticker", (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def add_to_bot_watchlist(user_id: int, ticker: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO bot_watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
                (user_id, ticker.upper(), now)
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def remove_from_bot_watchlist(user_id: int, ticker: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bot_watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper()))
        conn.commit()
        return cursor.rowcount > 0


def get_bot_signals(user_id: int, limit: int = 50) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bot_signals WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_bot_trades(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bot_trades WHERE user_id = ? ORDER BY entry_time DESC",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_closed_bot_trades(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bot_trades WHERE user_id = ? AND status = 'CLOSED' ORDER BY exit_time DESC",
            (user_id,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        if rows:
            return rows

    # Fallback to authoritative transactions ledger for bot trades
    return get_closed_trades(user_id, is_bot=True)


def get_open_bot_trades(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bot_trades WHERE user_id = ? AND status = 'OPEN' ORDER BY entry_time DESC",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def set_bot_active(user_id: int, is_active: bool) -> bool:
    """Toggles the is_active status in bot_configs for a user."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        # Ensure config exists first
        cursor.execute("SELECT 1 FROM bot_configs WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO bot_configs (user_id, is_active, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, 1 if is_active else 0, now, now)
            )
        else:
            cursor.execute(
                "UPDATE bot_configs SET is_active = ?, updated_at = ? WHERE user_id = ?",
                (1 if is_active else 0, now, user_id)
            )
        conn.commit()
        return True

# --- Social System ---

def create_follow(follower_id: int, following_id: int):
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_follows (follower_id, following_id, followed_at) VALUES (?, ?, ?)",
                (follower_id, following_id, now)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        pass


def delete_follow(follower_id: int, following_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_follows WHERE follower_id = ? AND following_id = ?", (follower_id, following_id))
        conn.commit()


def get_user_followers(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.* FROM users u
            JOIN user_follows f ON u.id = f.follower_id
            WHERE f.following_id = ?
            """,
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_user_following(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.* FROM users u
            JOIN user_follows f ON u.id = f.following_id
            WHERE f.follower_id = ?
            """,
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
