import unittest
import os
import json
import sqlite3
import tempfile
import sys
import time
import shutil

# Ensure src/ is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from config import Config
import database
import trading_engine
import analytics_engine
from app import app


class TestPhaseFPortfolioAnalytics(unittest.TestCase):
    """
    Comprehensive isolated tests for Phase F: Portfolio & Performance Analytics.
    Tests all 18 mandatory scenarios using isolated temporary SQLite databases.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="phase_f_case_")
        self.db_path = os.path.join(self.temp_dir, "isolated_phase_f.db")
        os.environ['DATABASE_PATH'] = self.db_path
        os.environ['DB_PATH'] = self.db_path

        Config.DB_PATH = self.db_path

        database.init_db()

        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Seed test user with initial balance
        self.starting_balance = 100000.0
        self.user_email = f"analytics_{time.time()}@example.com"
        self.user_id = database.create_user(
            email=self.user_email,
            password_hash="hashed_pw",
            username="analytics_user"
        )
        database.update_user_balance(self.user_id, self.starting_balance)
        with database.get_connection() as conn:
            conn.execute("UPDATE users SET starting_balance = ? WHERE id = ?", (self.starting_balance, self.user_id))
            conn.commit()

        from flask_jwt_extended import create_access_token
        with self.app.app_context():
            token = create_access_token(identity=str(self.user_id))
            self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except Exception:
                pass
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # SCENARIO 1: Empty Portfolio
    # -------------------------------------------------------------------------
    def test_01_empty_portfolio(self):
        """Empty portfolio returns 0 active holdings, 0 market value, and safe null/zero metrics."""
        summary = trading_engine.get_portfolio_summary(self.user_id)
        self.assertEqual(len(summary['holdings']), 0)
        self.assertEqual(summary['total_invested'], 0.0)
        self.assertEqual(summary['total_market_value'], 0.0)
        self.assertEqual(summary['total_pnl'], 0.0)
        self.assertEqual(summary['cash_balance'], self.starting_balance)
        self.assertEqual(summary['buying_power'], self.starting_balance)
        self.assertEqual(summary['reserved_cash'], 0.0)

        perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        self.assertEqual(perf['total_invested'], 0.0)
        self.assertEqual(perf['total_value'], 0.0)
        self.assertEqual(perf['unrealized_pnl'], 0.0)
        self.assertIsNone(perf['unrealized_return_pct'])
        self.assertEqual(perf['realized_pnl'], 0.0)
        self.assertIsNone(perf['win_rate_raw'])

        # API endpoint check
        res = self.client.get('/api/positions', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(len(data['positions']), 0)
        self.assertEqual(data['total_pnl'], 0.0)

    # -------------------------------------------------------------------------
    # SCENARIO 2: One Profitable Open Position
    # -------------------------------------------------------------------------
    def test_02_one_profitable_open_position(self):
        """Buy 10 AAPL @ $100 ($1,000 cost). Market price $120 -> +$200 unrealized (+20%)."""
        database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 100.0)

        # Mock current market price
        orig_get_price = trading_engine.get_current_price
        trading_engine.get_current_price = lambda ticker: 120.0 if ticker == "AAPL" else 0.0

        try:
            summary = trading_engine.get_portfolio_summary(self.user_id)
            self.assertEqual(len(summary['holdings']), 1)
            h = summary['holdings'][0]
            self.assertEqual(h['shares'], 10.0)
            self.assertEqual(h['avg_price'], 100.0)
            self.assertEqual(h['total_invested'], 1000.0)
            self.assertEqual(h['market_value'], 1200.0)
            self.assertEqual(h['pnl'], 200.0)
            self.assertEqual(h['pnl_percent'], 20.0)
            self.assertTrue(h['price_available'])

            perf = analytics_engine.calculate_portfolio_performance(self.user_id)
            self.assertEqual(perf['total_value'], 1200.0)
            self.assertEqual(perf['unrealized_pnl'], 200.0)
            self.assertEqual(perf['unrealized_return_pct'], 20.0)
            self.assertEqual(perf['total_pnl'], 200.0)
        finally:
            trading_engine.get_current_price = orig_get_price

    # -------------------------------------------------------------------------
    # SCENARIO 3: One Losing Open Position
    # -------------------------------------------------------------------------
    def test_03_one_losing_open_position(self):
        """Buy 10 MSFT @ $200 ($2,000 cost). Market price $150 -> -$500 unrealized (-25%)."""
        database.execute_trade_atomic(self.user_id, "MSFT", "BUY", 10.0, 200.0)

        orig_get_price = trading_engine.get_current_price
        trading_engine.get_current_price = lambda ticker: 150.0 if ticker == "MSFT" else 0.0

        try:
            summary = trading_engine.get_portfolio_summary(self.user_id)
            h = summary['holdings'][0]
            self.assertEqual(h['market_value'], 1500.0)
            self.assertEqual(h['pnl'], -500.0)
            self.assertEqual(h['pnl_percent'], -25.0)

            perf = analytics_engine.calculate_portfolio_performance(self.user_id)
            self.assertEqual(perf['unrealized_pnl'], -500.0)
            self.assertEqual(perf['unrealized_return_pct'], -25.0)
        finally:
            trading_engine.get_current_price = orig_get_price

    # -------------------------------------------------------------------------
    # SCENARIO 4: Fully Closed Position
    # -------------------------------------------------------------------------
    def test_04_fully_closed_position(self):
        """Buy 10 GOOG @ $100 ($1,000), sell 10 GOOG @ $130 ($1,300) -> +$300 realized, 0 open holdings."""
        database.execute_trade_atomic(self.user_id, "GOOG", "BUY", 10.0, 100.0)
        res = database.execute_trade_atomic(self.user_id, "GOOG", "SELL", 10.0, 130.0)
        self.assertTrue(res['success'])
        self.assertEqual(res['realized_pnl'], 300.0)

        # Portfolio holding should be cleanly deleted
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(len(portfolio), 0)

        perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        self.assertEqual(perf['realized_pnl'], 300.0)
        self.assertEqual(perf['unrealized_pnl'], 0.0)
        self.assertEqual(perf['total_pnl'], 300.0)
        self.assertEqual(perf['total_trades'], 1)
        self.assertEqual(perf['winning_trades'], 1)
        self.assertEqual(perf['win_rate'], 100.0)

    # -------------------------------------------------------------------------
    # SCENARIO 5: Partial Sell using WAC
    # -------------------------------------------------------------------------
    def test_05_partial_sell_using_wac(self):
        """Buy 10 @ $100 ($1,000), Buy 10 @ $200 ($2,000) -> 20 @ WAC $150 ($3,000). Sell 5 @ $180 -> +$150 PnL."""
        database.execute_trade_atomic(self.user_id, "TSLA", "BUY", 10.0, 100.0)
        database.execute_trade_atomic(self.user_id, "TSLA", "BUY", 10.0, 200.0)

        res = database.execute_trade_atomic(self.user_id, "TSLA", "SELL", 5.0, 180.0)
        self.assertEqual(res['realized_pnl'], 150.0)
        self.assertEqual(res['remaining_shares'], 15.0)

        # Remaining cost basis must be exactly 15 * $150 = $2,250
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(portfolio[0]['shares'], 15.0)
        self.assertEqual(portfolio[0]['avg_buy_price'], 150.0)
        self.assertEqual(portfolio[0]['total_invested'], 2250.0)

    # -------------------------------------------------------------------------
    # SCENARIO 6: Multiple Buys and Partial Sell
    # -------------------------------------------------------------------------
    def test_06_multiple_buys_and_partial_sell(self):
        """Buy 10 @ $50 ($500), 10 @ $100 ($1,000), 10 @ $150 ($1,500) -> 30 @ WAC $100. Sell 15 @ $140 -> +$600 PnL."""
        database.execute_trade_atomic(self.user_id, "NVDA", "BUY", 10.0, 50.0)
        database.execute_trade_atomic(self.user_id, "NVDA", "BUY", 10.0, 100.0)
        database.execute_trade_atomic(self.user_id, "NVDA", "BUY", 10.0, 150.0)

        res = database.execute_trade_atomic(self.user_id, "NVDA", "SELL", 15.0, 140.0)
        self.assertEqual(res['realized_pnl'], 600.0)

        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(portfolio[0]['shares'], 15.0)
        self.assertEqual(portfolio[0]['avg_buy_price'], 100.0)
        self.assertEqual(portfolio[0]['total_invested'], 1500.0)

    # -------------------------------------------------------------------------
    # SCENARIO 7: Realized and Unrealized P&L Correctly Separated
    # -------------------------------------------------------------------------
    def test_07_realized_and_unrealized_pnl_cleanly_separated(self):
        """Closed trade (+300 realized) and active open position (+200 unrealized) remain cleanly separated."""
        # Closed trade
        database.execute_trade_atomic(self.user_id, "AMD", "BUY", 10.0, 100.0)
        database.execute_trade_atomic(self.user_id, "AMD", "SELL", 10.0, 130.0)

        # Open holding
        database.execute_trade_atomic(self.user_id, "INTC", "BUY", 10.0, 50.0)

        orig_get_price = trading_engine.get_current_price
        trading_engine.get_current_price = lambda ticker: 70.0 if ticker == "INTC" else 0.0

        try:
            perf = analytics_engine.calculate_portfolio_performance(self.user_id)
            self.assertEqual(perf['realized_pnl'], 300.0)
            self.assertEqual(perf['unrealized_pnl'], 200.0)
            self.assertEqual(perf['total_pnl'], 500.0)
        finally:
            trading_engine.get_current_price = orig_get_price

    # -------------------------------------------------------------------------
    # SCENARIO 8: Reserved Cash Excluded from Buying Power
    # -------------------------------------------------------------------------
    def test_08_reserved_cash_excluded_from_buying_power(self):
        """Open BUY limit order reserves cash, reducing buying power while leaving balance intact."""
        database.create_order(self.user_id, "AMZN", "BUY", "LIMIT", "CNC", 10.0, 150.0)

        cash = database.get_user_balance(self.user_id)
        reserved = database.get_user_reserved_cash(self.user_id)
        bp = database.get_user_buying_power(self.user_id)

        self.assertEqual(cash, 100000.0)
        self.assertEqual(reserved, 1500.0)
        self.assertEqual(bp, 98500.0)

    # -------------------------------------------------------------------------
    # SCENARIO 9: Reserved Cash Not Deducted Twice
    # -------------------------------------------------------------------------
    def test_09_reserved_cash_not_deducted_twice(self):
        """Total equity accounts for actual cash + market value without double-deducting reserved cash."""
        database.create_order(self.user_id, "AMZN", "BUY", "LIMIT", "CNC", 10.0, 150.0)

        summary = trading_engine.get_portfolio_summary(self.user_id)
        self.assertEqual(summary['cash_balance'], 100000.0)
        self.assertEqual(summary['reserved_cash'], 1500.0)
        self.assertEqual(summary['buying_power'], 98500.0)
        self.assertEqual(summary['total_equity'], 100000.0)

    # -------------------------------------------------------------------------
    # SCENARIO 10: Missing, Invalid, and Stale Price Handling
    # -------------------------------------------------------------------------
    def test_10_missing_invalid_price_handling(self):
        """Missing or <= 0 market price is marked unavailable; never fabricates $0 or avg purchase price."""
        database.execute_trade_atomic(self.user_id, "UNPRICED", "BUY", 10.0, 100.0)

        orig_get_price = trading_engine.get_current_price
        trading_engine.get_current_price = lambda ticker: 0.0

        try:
            summary = trading_engine.get_portfolio_summary(self.user_id)
            h = summary['holdings'][0]
            self.assertIsNone(h['current_price'])
            self.assertIsNone(h['market_value'])
            self.assertIsNone(h['pnl'])
            self.assertFalse(h['price_available'])
            self.assertFalse(summary['all_prices_available'])
            self.assertIsNone(summary['total_market_value'])
            self.assertIsNone(summary['total_pnl'])

            perf = analytics_engine.calculate_portfolio_performance(self.user_id)
            self.assertFalse(perf['all_prices_available'])
            self.assertIn("UNPRICED", perf['unpriced_tickers'])
            self.assertIsNone(perf['total_value'])
            self.assertIsNone(perf['unrealized_pnl'])

            # /api/positions response check
            res = self.client.get('/api/positions', headers=self.headers)
            pos_data = json.loads(res.data)
            p = pos_data['positions'][0]
            self.assertIsNone(p['ltp'])
            self.assertIsNone(p['pnl'])
            self.assertFalse(p['price_available'])
        finally:
            trading_engine.get_current_price = orig_get_price

    # -------------------------------------------------------------------------
    # SCENARIO 11: Zero Denominators and Undefined Return Metrics
    # -------------------------------------------------------------------------
    def test_11_zero_denominators_and_undefined_returns(self):
        """Zero active capital, zero starting balance, or zero closed cost basis returns None without division errors."""
        perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        self.assertIsNone(perf['unrealized_return_pct'])
        self.assertIsNone(perf['realized_return_pct'])

        # Trade with zero cost basis edge test
        trade_stats = analytics_engine._compute_trade_stats([])
        self.assertIsNone(trade_stats['win_rate'])
        self.assertIsNone(trade_stats['avg_profit'])
        self.assertIsNone(trade_stats['avg_loss'])
        self.assertIsNone(trade_stats['profit_factor'])

    # -------------------------------------------------------------------------
    # SCENARIO 12: Bot vs Manual Attribution
    # -------------------------------------------------------------------------
    def test_12_bot_and_manual_attribution(self):
        """Bot and manual trades are strictly partitioned by is_bot field."""
        # Manual closed trade: +$100
        database.execute_trade_atomic(self.user_id, "MANUAL", "BUY", 10.0, 100.0, is_bot=False)
        database.execute_trade_atomic(self.user_id, "MANUAL", "SELL", 10.0, 110.0, is_bot=False)

        # Bot closed trade: +$250
        database.execute_trade_atomic(self.user_id, "BOT", "BUY", 10.0, 100.0, is_bot=True)
        database.execute_trade_atomic(self.user_id, "BOT", "SELL", 10.0, 125.0, is_bot=True)

        perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        self.assertEqual(perf['total_trades'], 2)
        self.assertEqual(perf['realized_pnl'], 350.0)

        # Bot partition
        self.assertEqual(perf['bot_performance']['total_trades'], 1)
        self.assertEqual(perf['bot_performance']['total_pnl'], 250.0)
        self.assertEqual(perf['bot_performance']['win_rate'], 100.0)

        # Manual partition
        self.assertEqual(perf['manual_performance']['total_trades'], 1)
        self.assertEqual(perf['manual_performance']['total_pnl'], 100.0)
        self.assertEqual(perf['manual_performance']['win_rate'], 100.0)

    # -------------------------------------------------------------------------
    # SCENARIO 13: No Duplicate Counting Across Tables
    # -------------------------------------------------------------------------
    def test_13_no_duplicate_counting_across_tables(self):
        """A bot trade existing in both bot_trades and transactions is counted exactly once."""
        from trading_bot.bot_engine import TradingBotEngine
        bot_engine = TradingBotEngine(db_path=self.db_path)
        bot_config = {"max_trades_per_day": 5, "max_position_size": 2000.0, "risk_level": "LOW", "stop_loss_pct": 0.05, "take_profit_pct": 0.1}

        signal = {
            "ticker": "DUPE", "action": "BUY", "confidence": 0.8,
            "sentiment_score": 0.5, "technical_score": 0.6, "ml_score": 0.7,
            "price": 100.0, "shares": 5, "stop_loss": 90.0, "take_profit": 120.0,
            "reasoning": "Dupe test"
        }
        bot_engine._execute_bot_trade(self.user_id, signal, bot_config)
        open_pos = database.get_open_bot_trades(self.user_id)[0]
        with database.get_connection() as conn:
            bot_engine._close_bot_position(self.user_id, open_pos, exit_price=120.0, exit_reason="TAKE_PROFIT", conn=conn)

        # Query analytics performance
        perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        # Exactly 1 closed trade (+100 PnL)
        self.assertEqual(perf['total_trades'], 1)
        self.assertEqual(perf['realized_pnl'], 100.0)
        self.assertEqual(perf['bot_performance']['total_trades'], 1)
        self.assertEqual(perf['bot_performance']['total_pnl'], 100.0)

    # -------------------------------------------------------------------------
    # SCENARIO 14: Empty Closed-Trade History and Win-Rate Behavior
    # -------------------------------------------------------------------------
    def test_14_empty_closed_trade_history_and_win_rate(self):
        """Zero closed trades results in 0 trades, None win rate, and zero PnL."""
        res = self.client.get('/api/bot/performance', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        bot_perf = json.loads(res.data)
        self.assertEqual(bot_perf['total_trades'], 0)
        self.assertEqual(bot_perf['win_rate'], 0.0)
        self.assertEqual(bot_perf['total_pnl'], 0.0)

    # -------------------------------------------------------------------------
    # SCENARIO 15: Historical Data with Unknown Attribution
    # -------------------------------------------------------------------------
    def test_15_historical_data_with_unknown_attribution(self):
        """Transactions with is_bot = NULL are placed in unattributed_performance and not assumed manual."""
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO transactions (user_id, ticker, action, shares, price_per_share, total_value, is_bot, realized_pnl, timestamp)
                VALUES (?, 'HIST', 'BUY', 10.0, 50.0, 500.0, NULL, 0.0, '2025-01-01T00:00:00Z')
                """,
                (self.user_id,)
            )
            cursor.execute(
                """
                INSERT INTO transactions (user_id, ticker, action, shares, price_per_share, total_value, is_bot, realized_pnl, timestamp)
                VALUES (?, 'HIST', 'SELL', 10.0, 70.0, 700.0, NULL, 200.0, '2025-01-02T00:00:00Z')
                """,
                (self.user_id,)
            )
            conn.commit()

        perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        self.assertEqual(perf['realized_pnl'], 200.0)
        # Must not be attributed to bot or manual
        self.assertEqual(perf['bot_performance']['total_trades'], 0)
        self.assertEqual(perf['manual_performance']['total_trades'], 0)
        self.assertEqual(perf['unattributed_performance']['total_trades'], 1)
        self.assertEqual(perf['unattributed_performance']['total_pnl'], 200.0)

    # -------------------------------------------------------------------------
    # SCENARIO 16: Analytics Endpoints Consistency
    # -------------------------------------------------------------------------
    def test_16_analytics_endpoints_consistency(self):
        """Endpoints /api/positions, /api/orders/buying-power, and /api/analytics/summary report matching figures."""
        database.execute_trade_atomic(self.user_id, "CONSIST", "BUY", 10.0, 100.0)
        database.create_order(self.user_id, "LIMITR", "BUY", "LIMIT", "CNC", 5.0, 200.0)

        res_bp = self.client.get('/api/orders/buying-power', headers=self.headers)
        data_bp = json.loads(res_bp.data)

        res_sum = self.client.get('/api/analytics/summary', headers=self.headers)
        data_sum = json.loads(res_sum.data)

        res_port = self.client.get('/api/portfolio', headers=self.headers)
        data_port = json.loads(res_port.data)['data']

        # Cash balances must match across all endpoints
        self.assertEqual(data_bp['cash_balance'], data_sum['cash_balance'])
        self.assertEqual(data_bp['reserved_cash'], data_sum['reserved_cash'])
        self.assertEqual(data_bp['buying_power'], data_sum['buying_power'])

        self.assertEqual(data_port['cash_balance'], data_sum['cash_balance'])
        self.assertEqual(data_port['reserved_cash'], data_sum['reserved_cash'])
        self.assertEqual(data_port['buying_power'], data_sum['buying_power'])

    # -------------------------------------------------------------------------
    # SCENARIO 17: Database Rollback Behavior
    # -------------------------------------------------------------------------
    def test_17_atomic_rollback_preserves_analytics_state(self):
        """A failed trade rolls back atomically leaving portfolio, cash, and analytics completely intact."""
        initial_perf = analytics_engine.calculate_portfolio_performance(self.user_id)

        # Attempt to sell shares not owned
        res = database.execute_trade_atomic(self.user_id, "NONEXIST", "SELL", 10.0, 100.0)
        self.assertFalse(res['success'])

        post_perf = analytics_engine.calculate_portfolio_performance(self.user_id)
        self.assertEqual(initial_perf['cash_balance'], post_perf['cash_balance'])
        self.assertEqual(initial_perf['total_invested'], post_perf['total_invested'])
        self.assertEqual(initial_perf['realized_pnl'], post_perf['realized_pnl'])

    # -------------------------------------------------------------------------
    # SCENARIO 18: Existing Phase D and Phase E Accounting Intact
    # -------------------------------------------------------------------------
    def test_18_existing_phase_d_and_e_accounting_intact(self):
        """WAC ledger accounting, atomic limit price matching, and reservations function seamlessly together."""
        # Buy 10 @ $100
        database.execute_trade_atomic(self.user_id, "INTEG", "BUY", 10.0, 100.0)

        # Place pending sell limit order for 4 shares @ $150
        order_id = database.create_order(self.user_id, "INTEG", "SELL", "LIMIT", "CNC", 4.0, 150.0)

        # Reserved shares must be 4, available shares must be 6
        self.assertEqual(database.get_user_reserved_shares(self.user_id, "INTEG"), 4.0)
        self.assertEqual(database.get_user_available_shares(self.user_id, "INTEG"), 6.0)

        # Owned shares in portfolio remain 10 (pending sell does not reduce owned inventory)
        portfolio = database.get_user_portfolio(self.user_id)
        self.assertEqual(portfolio[0]['shares'], 10.0)

        # Fill the sell order atomically at $150
        fill_res = database.fill_order_atomic(order_id, execution_price=150.0)
        self.assertTrue(fill_res['success'])
        # Realized PnL: 4 * (150 - 100) = $200
        self.assertEqual(fill_res['realized_pnl'], 200.0)

        # Remaining shares = 6, reserved shares = 0
        self.assertEqual(database.get_user_reserved_shares(self.user_id, "INTEG"), 0.0)
        self.assertEqual(database.get_user_available_shares(self.user_id, "INTEG"), 6.0)


if __name__ == '__main__':
    unittest.main()
