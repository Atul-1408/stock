"""Phase D Regression Test Suite: Financial Ledger Remediation.

Validates the Unified Ledger, Weighted-Average Cost (WAC) accounting,
shared cash balance, bot attribution, positions API, and duplicate detection.
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Configure testing environment before importing local modules
os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "phase4-ledger-remediation-test-secret-key-32-bytes!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# Standalone fallback: ensure an isolated temporary DB is used if not running via pytest conftest
if "DATABASE_PATH" not in os.environ and "DB_PATH" not in os.environ:
    import tempfile
    _test_tmp_dir = tempfile.mkdtemp(prefix="phase4_ledger_isolated_db_")
    _test_db_path = os.path.join(_test_tmp_dir, "test_phase4_ledger_isolated.db")
    os.environ["DATABASE_PATH"] = _test_db_path
    os.environ["DB_PATH"] = _test_db_path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
from app import app
from config import Config
from trading_bot.bot_engine import TradingBotEngine
import analytics_engine


class TestPhase4LedgerRemediation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        database.init_db()

        # Seed test user
        cls.test_email = "ledger_tester@sovereign.internal"
        cls.test_password = "SecurePassword123!"
        cls.test_username = "ledger_tester"

        # Register & Login
        cls.client.post("/api/auth/signup", json={
            "email": cls.test_email,
            "password": cls.test_password,
            "username": cls.test_username,
            "full_name": "Ledger Tester"
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
        # Reset balance to known amount $50,000 for each test
        database.update_user_balance(self.user_id, 50000.0)
        # Clear portfolio, transactions, orders, bot trades for this user
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM portfolio WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM transactions WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM orders WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM bot_trades WHERE user_id = ?", (self.user_id,))
            cursor.execute("DELETE FROM bot_signals WHERE user_id = ?", (self.user_id,))
            conn.commit()

    # -------------------------------------------------------------
    # 1. MANUAL TRADING & WEIGHTED-AVERAGE COST (WAC)
    # -------------------------------------------------------------
    def test_01_manual_buy_updates_balance_and_portfolio_wac(self):
        """Test multiple buys calculate correct Weighted-Average Cost."""
        # 1st Buy: 10 AAPL @ $100 ($1,000 total)
        res1 = database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 100.0, is_bot=False)
        self.assertTrue(res1["success"])
        self.assertEqual(res1["new_balance"], 49000.0)

        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(len(portfolio), 1)
        self.assertEqual(portfolio[0]["shares"], 10.0)
        self.assertEqual(portfolio[0]["avg_buy_price"], 100.0)
        self.assertEqual(portfolio[0]["total_invested"], 1000.0)

        # 2nd Buy: 10 AAPL @ $200 ($2,000 total)
        res2 = database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 200.0, is_bot=False)
        self.assertTrue(res2["success"])
        self.assertEqual(res2["new_balance"], 47000.0)

        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(portfolio[0]["shares"], 20.0)
        self.assertEqual(portfolio[0]["avg_buy_price"], 150.0)  # (1000 + 2000) / 20 = 150.0
        self.assertEqual(portfolio[0]["total_invested"], 3000.0)

        # Check attribution: manual trades have is_bot = 0
        txs = database.get_transactions_by_user(self.user_id)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0]["is_bot"], 0)
        self.assertEqual(txs[1]["is_bot"], 0)

    def test_02_manual_partial_sell_maintains_wac_and_records_realized_pnl(self):
        """Test partial sell credits balance, preserves WAC per share, and logs realized P&L."""
        # Establish position: 20 shares @ WAC $150 ($3,000 invested)
        database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 100.0)
        database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 200.0)

        # Sell 10 shares @ $250 ($2,500 proceeds)
        # Expected Realized P&L: 10 * (250 - 150) = $1,000.00
        res = database.execute_trade_atomic(self.user_id, "AAPL", "SELL", 10.0, 250.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["new_balance"], 49500.0)  # 47000 + 2500
        self.assertEqual(res["realized_pnl"], 1000.0)

        # Check remaining portfolio
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(len(portfolio), 1)
        self.assertEqual(portfolio[0]["shares"], 10.0)
        self.assertEqual(portfolio[0]["avg_buy_price"], 150.0)  # WAC preserved
        self.assertEqual(portfolio[0]["total_invested"], 1500.0)

        # Check closed trades report
        closed = database.get_closed_trades(self.user_id)
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0]["pnl"], 1000.0)
        self.assertEqual(closed[0]["buy_price"], 150.0)
        self.assertEqual(closed[0]["sell_price"], 250.0)

    def test_03_manual_full_sell_removes_holding_from_portfolio(self):
        """Test selling entire position cleans up portfolio row with zero shares remaining."""
        database.execute_trade_atomic(self.user_id, "TSLA", "BUY", 5.0, 200.0)
        res = database.execute_trade_atomic(self.user_id, "TSLA", "SELL", 5.0, 240.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["realized_pnl"], 200.0)  # 5 * (240 - 200)

        portfolio = database.get_user_portfolio(self.user_id)
        tsla_holding = [h for h in portfolio if h["ticker"] == "TSLA"]
        self.assertEqual(len(tsla_holding), 0)

    # -------------------------------------------------------------
    # 2. AUTONOMOUS BOT TRADING ON UNIFIED LEDGER
    # -------------------------------------------------------------
    def test_04_bot_buy_and_sell_unified_with_shared_cash(self):
        """Test that bot trades debit/credit shared user balance and update portfolio."""
        bot_engine = TradingBotEngine(db_path=os.environ.get("DATABASE_PATH", str(Config.DB_PATH)))
        bot_config = {
            "max_trades_per_day": 10,
            "max_position_size": 5000.0,
            "risk_level": "MEDIUM",
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.1
        }

        # 1. Bot BUY signal: 10 MSFT @ $300 ($3,000)
        buy_signal = {
            "ticker": "MSFT",
            "action": "BUY",
            "confidence": 0.92,
            "sentiment_score": 0.85,
            "technical_score": 0.88,
            "ml_score": 0.86,
            "price": 300.0,
            "shares": 10,
            "stop_loss": 285.0,
            "take_profit": 330.0,
            "reasoning": "Strong AI Momentum"
        }

        balance_before = database.get_user_balance(self.user_id)
        bot_engine._execute_bot_trade(self.user_id, buy_signal, bot_config)

        # Assert user cash balance was debited by $3,000
        balance_after_buy = database.get_user_balance(self.user_id)
        self.assertEqual(balance_after_buy, balance_before - 3000.0)

        # Assert MSFT is in user's portfolio
        portfolio = database.get_user_portfolio(self.user_id)
        msft = next((h for h in portfolio if h["ticker"] == "MSFT"), None)
        self.assertIsNotNone(msft)
        self.assertEqual(msft["shares"], 10.0)
        self.assertEqual(msft["avg_buy_price"], 300.0)

        # Assert bot attribution flag is 1
        txs = database.get_transactions_by_user(self.user_id)
        bot_tx = next((t for t in txs if t["ticker"] == "MSFT"), None)
        self.assertIsNotNone(bot_tx)
        self.assertEqual(bot_tx["is_bot"], 1)

        # 2. Bot Take-Profit SELL: 10 MSFT @ $330 ($3,300 proceeds, $300 profit)
        open_bot_trades = database.get_open_bot_trades(self.user_id)
        self.assertEqual(len(open_bot_trades), 1)
        position = open_bot_trades[0]

        with database.get_connection() as conn:
            bot_engine._close_bot_position(self.user_id, position, exit_price=330.0, exit_reason="TAKE_PROFIT", conn=conn)

        # Assert cash was credited by $3,300
        balance_after_sell = database.get_user_balance(self.user_id)
        self.assertEqual(balance_after_sell, balance_after_buy + 3300.0)

        # Assert portfolio holding was cleared
        portfolio_after_sell = database.get_user_portfolio(self.user_id)
        msft_after = next((h for h in portfolio_after_sell if h["ticker"] == "MSFT"), None)
        self.assertIsNone(msft_after)

        # Assert bot_trades closed with pnl = 300.0
        closed_bot = database.get_closed_bot_trades(self.user_id)
        self.assertEqual(len(closed_bot), 1)
        self.assertEqual(closed_bot[0]["status"], "CLOSED")
        self.assertEqual(closed_bot[0]["pnl"], 300.0)
        self.assertEqual(closed_bot[0]["exit_reason"], "TAKE_PROFIT")

    # -------------------------------------------------------------
    # 3. SAFETY, FAILED TRANSACTIONS & ROLLBACK
    # -------------------------------------------------------------
    def test_05_insufficient_funds_fails_atomically_and_rolls_back(self):
        """Test buy exceeding balance is rejected without partial updates."""
        database.update_user_balance(self.user_id, 500.0)

        res = database.execute_trade_atomic(self.user_id, "NVDA", "BUY", 10.0, 100.0)  # $1,000 required
        self.assertFalse(res["success"])
        self.assertIn("Insufficient funds", res["message"])

        # Check atomicity: balance untouched, no portfolio item, no transaction
        self.assertEqual(database.get_user_balance(self.user_id), 500.0)
        self.assertEqual(len(database.get_user_portfolio(self.user_id)), 0)
        self.assertEqual(len(database.get_transactions_by_user(self.user_id)), 0)
        self.assertEqual(len(database.get_user_orders(self.user_id)), 0)

    def test_06_insufficient_shares_fails_atomically_and_rolls_back(self):
        """Test sell exceeding owned shares is rejected without partial updates."""
        database.execute_trade_atomic(self.user_id, "AMD", "BUY", 5.0, 100.0)
        bal_before = database.get_user_balance(self.user_id)

        res = database.execute_trade_atomic(self.user_id, "AMD", "SELL", 10.0, 150.0)
        self.assertFalse(res["success"])
        self.assertIn("Insufficient shares", res["message"])

        # Check atomicity: balance and shares untouched
        self.assertEqual(database.get_user_balance(self.user_id), bal_before)
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(portfolio[0]["shares"], 5.0)

    # -------------------------------------------------------------
    # 4. POSITIONS API REGRESSION
    # -------------------------------------------------------------
    def test_07_positions_api_returns_actual_shares_and_pnl(self):
        """Test /api/positions correctly parses avg_buy_price and shares."""
        database.execute_trade_atomic(self.user_id, "GOOGL", "BUY", 10.0, 150.0)

        # Seed market data cache so LTP is deterministic
        database.upsert_market_cache({"symbol": "GOOGL", "last_price": 170.0})

        res = self.client.get("/api/positions", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)

        positions = data.get("positions", [])
        self.assertEqual(len(positions), 1)
        pos = positions[0]
        self.assertEqual(pos["symbol"], "GOOGL")
        self.assertEqual(pos["quantity"], 10.0)
        self.assertEqual(pos["avg_price"], 150.0)
        self.assertEqual(pos["ltp"], 170.0)
        self.assertEqual(pos["current_value"], 1700.0)
        self.assertEqual(pos["pnl"], 200.0)
        self.assertEqual(pos["pnl_pct"], 13.33)

    # -------------------------------------------------------------
    # 5. DUPLICATE ORDER DETECTION ON /api/trade
    # -------------------------------------------------------------
    def test_08_duplicate_order_prevention_on_api_trade(self):
        """Test /api/trade rejects rapid duplicate submission with 409 Conflict."""
        # Seed AAPL in universe for pricing
        database.upsert_market_cache({"symbol": "AAPL", "last_price": 150.0})

        # First request
        res1 = self.client.post("/api/trade", headers=self.headers, json={
            "ticker": "AAPL",
            "action": "BUY",
            "shares": 1
        })
        self.assertEqual(res1.status_code, 200)

        # Immediate duplicate request
        res2 = self.client.post("/api/trade", headers=self.headers, json={
            "ticker": "AAPL",
            "action": "BUY",
            "shares": 1
        })
        self.assertEqual(res2.status_code, 409)
        data2 = json.loads(res2.data)
        self.assertIn("Duplicate order detected", data2.get("message", ""))

    # -------------------------------------------------------------
    # 6. BOT ENDPOINTS ACCURACY & SEPARATION
    # -------------------------------------------------------------
    def test_09_bot_endpoints_isolated_from_manual_trades(self):
        """Test /api/bot/trades and /api/bot/performance evaluate actual bot records."""
        # 1. Manual trade
        database.execute_trade_atomic(self.user_id, "AMZN", "BUY", 2.0, 100.0, is_bot=False)

        # 2. Bot trade
        bot_engine = TradingBotEngine(db_path=os.environ.get("DATABASE_PATH", str(Config.DB_PATH)))
        bot_config = {"max_trades_per_day": 10, "max_position_size": 2000.0, "risk_level": "LOW", "stop_loss_pct": 0.05, "take_profit_pct": 0.1}
        signal = {
            "ticker": "NFLX", "action": "BUY", "confidence": 0.8,
            "sentiment_score": 0.5, "technical_score": 0.6, "ml_score": 0.7,
            "price": 200.0, "shares": 1, "stop_loss": 190.0, "take_profit": 220.0,
            "reasoning": "Bot pick"
        }
        bot_engine._execute_bot_trade(self.user_id, signal, bot_config)

        # Query /api/bot/trades
        res = self.client.get("/api/bot/trades", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        bot_trades = json.loads(res.data).get("trades", [])

        # Assert only bot trade (NFLX) is returned, manual trade (AMZN) is NOT included
        symbols = [t["ticker"] for t in bot_trades]
        self.assertIn("NFLX", symbols)
        self.assertNotIn("AMZN", symbols)

    # -------------------------------------------------------------
    # 7. ANALYTICS CUMULATIVE BUY BUG FIX
    # -------------------------------------------------------------
    def test_10_analytics_closed_trades_does_not_produce_negative_phantom_loss(self):
        """Test that selling profitable shares produces positive return, not negative loss."""
        # Buy $1,000 of stock
        database.execute_trade_atomic(self.user_id, "META", "BUY", 10.0, 100.0)
        # Sell entire position for $1,200 ($200 realized profit)
        database.execute_trade_atomic(self.user_id, "META", "SELL", 10.0, 120.0)

        perf = analytics_engine.calculate_portfolio_performance(self.user_id)

        # Closed position: active holdings value is 0, active invested is 0
        self.assertEqual(perf["total_value"], 0.0)
        self.assertEqual(perf["total_invested"], 0.0)
        self.assertEqual(perf["realized_pnl"], 200.0)
        self.assertEqual(perf["total_pnl"], 200.0)
        self.assertGreaterEqual(perf["total_pnl_pct"], 0.0)  # Must NOT be -100%!
        self.assertEqual(perf["win_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
