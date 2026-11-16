"""Phase D Comprehensive Post-Implementation Verification & Edge-Case Suite.

Thoroughly tests:
1. Edge cases A through L (Unified ledger, WAC, bot isolation, positions API, analytics).
2. Migration safety (fresh DB init, repeated init, legacy DB compatibility, idempotency).
3. Atomic rollback and consistency guarantees.
All tests run against temporary, isolated databases.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

# Configure testing environment
os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "verification-edge-case-secret-key-32-bytes!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# Standalone fallback: ensure an isolated temporary DB is used
if "DATABASE_PATH" not in os.environ and "DB_PATH" not in os.environ:
    _test_tmp_dir = tempfile.mkdtemp(prefix="phase4_edge_case_db_")
    _test_db_path = os.path.join(_test_tmp_dir, "test_edge_cases.db")
    os.environ["DATABASE_PATH"] = _test_db_path
    os.environ["DB_PATH"] = _test_db_path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
from app import app
from config import Config
from trading_bot.bot_engine import TradingBotEngine
import analytics_engine


class TestPhaseDVerificationEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        database.init_db()

        # Seed test user
        cls.test_email = "verifier@sovereign.internal"
        cls.test_password = "SecurePassword123!"
        cls.test_username = "verifier"

        cls.client.post("/api/auth/signup", json={
            "email": cls.test_email,
            "password": cls.test_password,
            "username": cls.test_username,
            "full_name": "Post-Implementation Verifier"
        })
        login_res = cls.client.post("/api/auth/login", json={
            "email": cls.test_email,
            "password": cls.test_password
        })
        login_data = json.loads(login_res.data)
        cls.token = login_data.get("access_token")
        cls.user_id = login_data.get("user_id")
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def setUp(self):
        database.update_user_balance(self.user_id, 50000.0)
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM portfolio WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM transactions WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM orders WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM bot_trades WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM bot_signals WHERE user_id = ?", (self.user_id,))
            conn.commit()

    # -------------------------------------------------------------------------
    # EDGE CASE A & C: MANUAL BUY AND BOT BUY OF SAME SYMBOL & SHARED CASH
    # -------------------------------------------------------------------------
    def test_edge_case_a_and_c_manual_and_bot_buy_same_symbol_share_cash(self):
        """Edge Case A & C: Manual BUY and Bot BUY on same symbol share cash and update WAC."""
        bot_engine = TradingBotEngine(db_path=os.environ.get("DATABASE_PATH", str(Config.DB_PATH)))
        bot_config = {"max_trades_per_day": 10, "max_position_size": 10000.0, "risk_level": "MED", "stop_loss_pct": 0.05, "take_profit_pct": 0.1}

        # Starting balance $50,000
        # 1. Manual BUY: 10 AAPL @ $150 ($1,500)
        res_manual = database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 150.0, is_bot=False)
        self.assertTrue(res_manual["success"])
        self.assertEqual(res_manual["new_balance"], 48500.0)

        # 2. Bot BUY: 10 AAPL @ $170 ($1,700)
        signal = {
            "ticker": "AAPL", "action": "BUY", "confidence": 0.9, "sentiment_score": 0.8,
            "technical_score": 0.85, "ml_score": 0.8, "price": 170.0, "shares": 10,
            "stop_loss": 160.0, "take_profit": 190.0, "reasoning": "Bot momentum"
        }
        bot_engine._execute_bot_trade(self.user_id, signal, bot_config)

        # Assert shared cash was debited for both: $50,000 - $1,500 - $1,700 = $46,800
        current_balance = database.get_user_balance(self.user_id)
        self.assertEqual(current_balance, 46800.0)

        # Assert combined holdings: 20 shares @ WAC $160 ((1500+1700)/20 = 160.0)
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(len(portfolio), 1)
        self.assertEqual(portfolio[0]["ticker"], "AAPL")
        self.assertEqual(portfolio[0]["shares"], 20.0)
        self.assertEqual(portfolio[0]["avg_buy_price"], 160.0)
        self.assertEqual(portfolio[0]["total_invested"], 3200.0)

        # Assert attribution in audit records
        txs = database.get_transactions_by_user(self.user_id)
        self.assertEqual(len(txs), 2)
        bot_txs = [t for t in txs if t["is_bot"] == 1]
        manual_txs = [t for t in txs if t["is_bot"] == 0]
        self.assertEqual(len(bot_txs), 1)
        self.assertEqual(len(manual_txs), 1)

    # -------------------------------------------------------------------------
    # EDGE CASE B: CLOSING BOT POSITION PRESERVES UNRELATED MANUAL POSITION
    # -------------------------------------------------------------------------
    def test_edge_case_b_closing_bot_position_preserves_manual_position(self):
        """Edge Case B: Closing a bot position does not close or misattribute user's manual position."""
        bot_engine = TradingBotEngine(db_path=os.environ.get("DATABASE_PATH", str(Config.DB_PATH)))
        bot_config = {"max_trades_per_day": 10, "max_position_size": 10000.0, "risk_level": "MED", "stop_loss_pct": 0.05, "take_profit_pct": 0.1}

        # 1. User manual BUY 10 AAPL @ $150
        database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 150.0, is_bot=False)

        # 2. Bot BUY 10 AAPL @ $170
        signal = {
            "ticker": "AAPL", "action": "BUY", "confidence": 0.9, "sentiment_score": 0.8,
            "technical_score": 0.85, "ml_score": 0.8, "price": 170.0, "shares": 10,
            "stop_loss": 160.0, "take_profit": 190.0, "reasoning": "Bot buy"
        }
        bot_engine._execute_bot_trade(self.user_id, signal, bot_config)

        # 3. Bot closes its position: SELL 10 AAPL @ $190
        open_bot_trades = database.get_open_bot_trades(self.user_id)
        self.assertEqual(len(open_bot_trades), 1)
        bot_pos = open_bot_trades[0]

        with database.get_connection() as conn:
            bot_engine._close_bot_position(self.user_id, bot_pos, exit_price=190.0, exit_reason="TAKE_PROFIT", conn=conn)

        # Assert manual position remains open with 10 shares
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(len(portfolio), 1)
        self.assertEqual(portfolio[0]["ticker"], "AAPL")
        self.assertEqual(portfolio[0]["shares"], 10.0)
        self.assertEqual(portfolio[0]["avg_buy_price"], 160.0)  # Preserved WAC
        self.assertEqual(portfolio[0]["total_invested"], 1600.0)

        # Assert bot trade is closed with proper attribution
        closed_bot = database.get_closed_bot_trades(self.user_id)
        self.assertEqual(len(closed_bot), 1)
        self.assertEqual(closed_bot[0]["status"], "CLOSED")
        self.assertEqual(closed_bot[0]["exit_reason"], "TAKE_PROFIT")

    # -------------------------------------------------------------------------
    # EDGE CASE D: BOT-SPECIFIC P&L EXCLUDES MANUAL TRADES
    # -------------------------------------------------------------------------
    def test_edge_case_d_bot_pnl_strictly_excludes_manual_trades(self):
        """Edge Case D: Bot performance metrics must exclude manual trade P&L."""
        # 1. Manual BUY and profitable SELL: +$500 profit
        database.execute_trade_atomic(self.user_id, "TSLA", "BUY", 10.0, 200.0, is_bot=False)
        database.execute_trade_atomic(self.user_id, "TSLA", "SELL", 10.0, 250.0, is_bot=False)

        # 2. Bot BUY and losing SELL: -$50 loss
        bot_engine = TradingBotEngine(db_path=os.environ.get("DATABASE_PATH", str(Config.DB_PATH)))
        bot_config = {"max_trades_per_day": 10, "max_position_size": 2000.0, "risk_level": "MED", "stop_loss_pct": 0.05, "take_profit_pct": 0.1}
        signal = {
            "ticker": "NVDA", "action": "BUY", "confidence": 0.8, "sentiment_score": 0.6,
            "technical_score": 0.7, "ml_score": 0.65, "price": 100.0, "shares": 5,
            "stop_loss": 90.0, "take_profit": 120.0, "reasoning": "Bot setup"
        }
        bot_engine._execute_bot_trade(self.user_id, signal, bot_config)
        open_pos = database.get_open_bot_trades(self.user_id)[0]
        with database.get_connection() as conn:
            bot_engine._close_bot_position(self.user_id, open_pos, exit_price=90.0, exit_reason="STOP_LOSS", conn=conn)

        # Query /api/bot/performance
        res = self.client.get("/api/bot/performance", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        perf = json.loads(res.data)

        # Bot performance must only reflect NVDA (-$50 loss, 0 wins, 1 loss)
        self.assertEqual(perf["total_trades"], 1)
        self.assertEqual(perf["winning_trades"], 0)
        self.assertEqual(perf["losing_trades"], 1)
        self.assertEqual(perf["total_pnl"], -50.0)
        self.assertEqual(perf["win_rate"], 0.0)

    # -------------------------------------------------------------------------
    # EDGE CASE E & F: PARTIAL AND FULL SELL WAC INTEGRITY
    # -------------------------------------------------------------------------
    def test_edge_case_e_and_f_partial_and_full_sell_wac_integrity(self):
        """Edge Case E & F: Partial sell maintains WAC; full sell cleans portfolio and records P&L."""
        # Buy 10 @ $100 ($1,000), Buy 10 @ $200 ($2,000) -> 20 @ WAC $150 ($3,000)
        database.execute_trade_atomic(self.user_id, "INTC", "BUY", 10.0, 100.0)
        database.execute_trade_atomic(self.user_id, "INTC", "BUY", 10.0, 200.0)

        # Partial SELL: 5 shares @ $180 ($900 proceeds)
        # Expected Realized P&L: 5 * (180 - 150) = $150.00
        res_part = database.execute_trade_atomic(self.user_id, "INTC", "SELL", 5.0, 180.0)
        self.assertTrue(res_part["success"])
        self.assertEqual(res_part["realized_pnl"], 150.0)

        # 15 shares remain @ WAC $150.0, total invested = $2,250.0
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(portfolio[0]["shares"], 15.0)
        self.assertEqual(portfolio[0]["avg_buy_price"], 150.0)
        self.assertEqual(portfolio[0]["total_invested"], 2250.0)

        # Full SELL: remaining 15 shares @ $210 ($3,150 proceeds)
        # Expected Realized P&L: 15 * (210 - 150) = $900.00
        res_full = database.execute_trade_atomic(self.user_id, "INTC", "SELL", 15.0, 210.0)
        self.assertTrue(res_full["success"])
        self.assertEqual(res_full["realized_pnl"], 900.0)

        # Portfolio holding must be completely removed
        portfolio_after = database.get_user_portfolio(self.user_id)
        intc_holding = [h for h in portfolio_after if h["ticker"] == "INTC"]
        self.assertEqual(len(intc_holding), 0)

    # -------------------------------------------------------------------------
    # EDGE CASE G & H: INSUFFICIENT FUNDS & TRANSACTION ROLLBACK SAFETY
    # -------------------------------------------------------------------------
    def test_edge_case_g_and_h_insufficient_funds_and_atomic_rollback(self):
        """Edge Case G & H: Insufficient funds & errors leave zero partial accounting updates."""
        database.update_user_balance(self.user_id, 300.0)

        # 1. Insufficient funds check
        res = database.execute_trade_atomic(self.user_id, "AMZN", "BUY", 5.0, 100.0)  # $500 required
        self.assertFalse(res["success"])
        self.assertIn("Insufficient funds", res["message"])

        # Assert no side-effects
        self.assertEqual(database.get_user_balance(self.user_id), 300.0)
        self.assertEqual(len(database.get_user_portfolio(self.user_id)), 0)
        self.assertEqual(len(database.get_transactions_by_user(self.user_id)), 0)
        self.assertEqual(len(database.get_user_orders(self.user_id)), 0)

        # 2. Simulate internal database exception during execution
        with unittest.mock.patch("database.get_connection") as mock_conn:
            fake_conn = unittest.mock.MagicMock()
            fake_cursor = unittest.mock.MagicMock()
            fake_cursor.fetchone.side_effect = sqlite3.OperationalError("Simulated DB Disk Failure")
            fake_conn.cursor.return_value = fake_cursor
            mock_conn.return_value = fake_conn

            with self.assertRaises(sqlite3.OperationalError):
                database.execute_trade_atomic(self.user_id, "AMZN", "BUY", 1.0, 100.0)
            fake_conn.rollback.assert_called()

    # -------------------------------------------------------------------------
    # EDGE CASE I: DUPLICATE ORDER DETECTION
    # -------------------------------------------------------------------------
    def test_edge_case_i_duplicate_order_detection(self):
        """Edge Case I: Rapid duplicate requests cannot double-debit cash balance."""
        database.upsert_market_cache({"symbol": "AAPL", "last_price": 150.0})
        bal_start = database.get_user_balance(self.user_id)

        # 1st request
        r1 = self.client.post("/api/trade", headers=self.headers, json={"ticker": "AAPL", "action": "BUY", "shares": 1})
        self.assertEqual(r1.status_code, 200)

        # Duplicate request within window
        r2 = self.client.post("/api/trade", headers=self.headers, json={"ticker": "AAPL", "action": "BUY", "shares": 1})
        self.assertEqual(r2.status_code, 409)

        # Balance debited only once for 1 share @ $150
        bal_end = database.get_user_balance(self.user_id)
        self.assertEqual(bal_end, bal_start - 150.0)

    # -------------------------------------------------------------------------
    # EDGE CASE J: POSITIONS API ACCURACY
    # -------------------------------------------------------------------------
    def test_edge_case_j_positions_api_returns_actual_shares_and_cost(self):
        """Edge Case J: /api/positions accurately reports non-zero quantity and avg_price."""
        database.execute_trade_atomic(self.user_id, "MSFT", "BUY", 25.0, 320.0)
        database.upsert_market_cache({"symbol": "MSFT", "last_price": 350.0})

        res = self.client.get("/api/positions", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)

        pos = next((p for p in data.get("positions", []) if p["symbol"] == "MSFT"), None)
        self.assertIsNotNone(pos)
        self.assertEqual(pos["quantity"], 25.0)
        self.assertEqual(pos["avg_price"], 320.0)
        self.assertEqual(pos["ltp"], 350.0)
        self.assertEqual(pos["pnl"], 750.0)  # 25 * (350 - 320)
        self.assertEqual(pos["current_value"], 8750.0)

    # -------------------------------------------------------------------------
    # EDGE CASE K: PERFORMANCE ANALYTICS CLOSED TRADE ACCURACY
    # -------------------------------------------------------------------------
    def test_edge_case_k_closed_profitable_trade_has_positive_return(self):
        """Edge Case K: Closed profitable trade produces positive return, not negative loss."""
        database.execute_trade_atomic(self.user_id, "SPY", "BUY", 10.0, 400.0)
        database.execute_trade_atomic(self.user_id, "SPY", "SELL", 10.0, 450.0)  # +$500 profit

        perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        self.assertEqual(perf["total_value"], 0.0)
        self.assertEqual(perf["total_invested"], 0.0)
        self.assertEqual(perf["realized_pnl"], 500.0)
        self.assertEqual(perf["total_pnl"], 500.0)
        self.assertGreater(perf["total_pnl_pct"], 0.0)
        self.assertEqual(perf["win_rate"], 100.0)

    # -------------------------------------------------------------------------
    # EDGE CASE L: BOT ENDPOINTS RETURN ACCURATE DATA
    # -------------------------------------------------------------------------
    def test_edge_case_l_bot_endpoints_return_actual_bot_data(self):
        """Edge Case L: /api/bot/trades returns actual bot trade entries."""
        bot_engine = TradingBotEngine(db_path=os.environ.get("DATABASE_PATH", str(Config.DB_PATH)))
        bot_config = {"max_trades_per_day": 10, "max_position_size": 2000.0, "risk_level": "LOW", "stop_loss_pct": 0.05, "take_profit_pct": 0.1}
        signal = {
            "ticker": "CSCO", "action": "BUY", "confidence": 0.85, "sentiment_score": 0.7,
            "technical_score": 0.75, "ml_score": 0.72, "price": 50.0, "shares": 10,
            "stop_loss": 47.5, "take_profit": 55.0, "reasoning": "CSCO Bot Signal"
        }
        bot_engine._execute_bot_trade(self.user_id, signal, bot_config)

        res = self.client.get("/api/bot/trades", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        trades = json.loads(res.data).get("trades", [])
        csco = next((t for t in trades if t["ticker"] == "CSCO"), None)
        self.assertIsNotNone(csco)
        self.assertEqual(csco["shares"], 10)
        self.assertEqual(csco["entry_price"], 50.0)
        self.assertEqual(csco["status"], "OPEN")


class TestPhaseDMigrationSafety(unittest.TestCase):
    """Tests schema migration idempotency, repeated inits, and legacy DB compatibility."""

    def test_migration_fresh_and_repeated_initialization(self):
        """Test init_db on a fresh database and repeated execution without errors."""
        temp_dir = tempfile.mkdtemp(prefix="phase4_migration_fresh_")
        fresh_db_path = os.path.join(temp_dir, "fresh.db")

        # Point Config to fresh DB
        orig_path = Config.DB_PATH
        try:
            Config.DB_PATH = Path(fresh_db_path)

            # 1. Fresh initialization
            database.init_db()

            # Verify columns exist
            with database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(transactions)")
                tx_cols = [r["name"] for r in cursor.fetchall()]
                self.assertIn("is_bot", tx_cols)
                self.assertIn("realized_pnl", tx_cols)

                cursor.execute("PRAGMA table_info(orders)")
                order_cols = [r["name"] for r in cursor.fetchall()]
                self.assertIn("is_bot", order_cols)

            # 2. Repeated initialization (idempotency check)
            database.init_db()
            database.init_db()

            # Verify no errors and columns still present
            with database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(transactions)")
                self.assertIn("is_bot", [r["name"] for r in cursor.fetchall()])

        finally:
            Config.DB_PATH = orig_path

    def test_migration_legacy_database_compatibility(self):
        """Test migrating an existing legacy database lacking is_bot and realized_pnl columns."""
        temp_dir = tempfile.mkdtemp(prefix="phase4_migration_legacy_")
        legacy_db_path = os.path.join(temp_dir, "legacy.db")

        # Create simulated legacy schema without is_bot and realized_pnl
        conn = sqlite3.connect(legacy_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                current_balance REAL DEFAULT 100000.00,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares REAL NOT NULL,
                price_per_share REAL NOT NULL,
                total_value REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                status TEXT DEFAULT 'OPEN',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # Insert historical data
        cursor.execute("INSERT INTO users (email, password_hash, created_at) VALUES ('legacy@example.com', 'hash', '2025-01-01')")
        cursor.execute("INSERT INTO transactions (user_id, ticker, action, shares, price_per_share, total_value, timestamp) VALUES (1, 'IBM', 'BUY', 10, 100, 1000, '2025-01-01')")
        cursor.execute("INSERT INTO orders (user_id, symbol, side, quantity, status, created_at, updated_at) VALUES (1, 'IBM', 'BUY', 10, 'FILLED', '2025-01-01', '2025-01-01')")
        conn.commit()
        conn.close()

        # Run init_db() on this legacy database
        orig_path = Config.DB_PATH
        try:
            Config.DB_PATH = Path(legacy_db_path)
            database.init_db()

            # Verify migrated columns and preserved historical records
            with database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, ticker, is_bot, realized_pnl FROM transactions WHERE id = 1")
                row = cursor.fetchone()
                self.assertEqual(row["ticker"], "IBM")
                self.assertEqual(row["is_bot"], 0)
                self.assertEqual(row["realized_pnl"], 0.0)

                cursor.execute("SELECT id, symbol, is_bot FROM orders WHERE id = 1")
                order_row = cursor.fetchone()
                self.assertEqual(order_row["symbol"], "IBM")
                self.assertEqual(order_row["is_bot"], 0)
        finally:
            Config.DB_PATH = orig_path


if __name__ == "__main__":
    unittest.main()
