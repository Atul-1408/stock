"""Phase E: Paper Trading Order Execution & Buying Power Regression Test Suite.

Rigorously tests:
A. BUY limit order placed below current market price remains pending.
B. BUY limit order executes when its price condition is met.
C. SELL limit order executes only when its price condition is met.
D. Multiple pending BUY orders cannot over-reserve available cash.
E. Insufficient buying power rejects order placement.
F. Filled BUY order converts reservation into cash debit exactly once.
G. Cancellation releases reserved buying power exactly once.
H. Expiration releases reserved buying power exactly once.
I. Repeated worker execution does not double-fill an order.
J. Concurrent order submissions cannot overspend buying power.
K. Fill and cancellation racing against each other cannot both succeed.
L. Missing or invalid market data does not trigger a fabricated-price fill.
M. Failed execution rolls back all related database changes.
N. SELL orders cannot sell more shares than the user owns.
O. WAC and realized P&L remain correct after limit-order fills.
P. Manual and bot order attribution remains correct.
Q. Existing market orders continue to behave correctly.
R. Fresh database initialization and repeated initialization remain safe.
S. Existing historical data remains intact.

All tests run strictly against isolated temporary SQLite databases.
"""

import concurrent.futures
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

# Configure isolated environment
os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "phase-e-paper-order-execution-secret-32b!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# Standalone fallback: ensure an isolated temporary DB is used
if "DATABASE_PATH" not in os.environ and "DB_PATH" not in os.environ:
    _test_tmp_dir = tempfile.mkdtemp(prefix="phase_e_test_db_")
    _test_db_path = os.path.join(_test_tmp_dir, "test_phase_e.db")
    os.environ["DATABASE_PATH"] = _test_db_path
    os.environ["DB_PATH"] = _test_db_path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
import trading_engine
from app import app
from flask_jwt_extended import create_access_token


class TestPhaseEOrderExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        # Create a fresh isolated SQLite database for each test
        self.temp_dir = tempfile.mkdtemp(prefix="phase_e_case_")
        self.db_path = os.path.join(self.temp_dir, "isolated_phase_e.db")
        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["DB_PATH"] = self.db_path

        from config import Config
        Config.DB_PATH = self.db_path

        database.init_db()

        # Create isolated primary test user
        self.user_email = f"trader_e_{int(time.time() * 1000)}@example.com"
        self.user_id = database.create_user("Trader E", self.user_email, "hashed_password_123")
        database.update_user_balance(self.user_id, 10000.0)

        with app.app_context():
            self.jwt_token = create_access_token(identity=str(self.user_id))
        self.headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    # -------------------------------------------------------------
    # EDGE CASE A: BUY Limit order placed below market price remains pending
    # -------------------------------------------------------------
    def test_case_a_buy_limit_below_market_price_remains_pending(self):
        """BUY limit order placed below market price remains OPEN."""
        # Current market price for NVDA is $150.0
        database.upsert_market_cache({"symbol": "NVDA", "last_price": 150.0})

        # User places BUY limit order for 10 NVDA @ $140.0 ($1,400 required)
        order_id = database.create_order(
            user_id=self.user_id,
            symbol="NVDA",
            side="BUY",
            order_type="LIMIT",
            product_type="CNC",
            quantity=10.0,
            price=140.0
        )
        self.assertGreater(order_id, 0)

        # Evaluate matching engine with current price at $150.0
        fills = trading_engine.match_pending_orders(symbol="NVDA")
        self.assertEqual(len(fills), 0, "Order must not fill when market price exceeds limit price")

        # Verify order remains OPEN
        orders = database.get_user_orders(self.user_id, status="OPEN")
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["id"], order_id)
        self.assertEqual(orders[0]["status"], "OPEN")

        # Verify buying power was reserved
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 1400.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 8600.0)
        self.assertEqual(database.get_user_balance(self.user_id), 10000.0)

    # -------------------------------------------------------------
    # EDGE CASE B: BUY Limit order executes when price condition is met
    # -------------------------------------------------------------
    def test_case_b_buy_limit_executes_when_condition_met(self):
        """BUY limit order fills when market price drops to or below limit price."""
        database.upsert_market_cache({"symbol": "MSFT", "last_price": 310.0})

        # Place BUY limit for 5 MSFT @ $300.0 ($1,500)
        order_id = database.create_order(
            user_id=self.user_id,
            symbol="MSFT",
            side="BUY",
            order_type="LIMIT",
            product_type="CNC",
            quantity=5.0,
            price=300.0
        )

        # Market price drops to $295.0 (satisfies <= $300.0)
        database.upsert_market_cache({"symbol": "MSFT", "last_price": 295.0})

        fills = trading_engine.match_pending_orders(symbol="MSFT")
        self.assertEqual(len(fills), 1)
        fill = fills[0]
        self.assertEqual(fill["order_id"], order_id)
        self.assertEqual(fill["filled_price"], 295.0)
        self.assertEqual(fill["total_value"], 1475.0)

        # Verify order is FILLED
        orders = database.get_user_orders(self.user_id)
        self.assertEqual(orders[0]["status"], "FILLED")
        self.assertEqual(orders[0]["filled_price"], 295.0)

        # Verify cash debit and buying power
        self.assertEqual(database.get_user_balance(self.user_id), 8525.0)  # 10,000 - 1,475
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 0.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 8525.0)

        # Verify portfolio
        shares = database.get_user_shares(self.user_id, "MSFT")
        self.assertEqual(shares, 5.0)

    # -------------------------------------------------------------
    # EDGE CASE C: SELL Limit order executes only when price condition is met
    # -------------------------------------------------------------
    def test_case_c_sell_limit_executes_only_when_condition_met(self):
        """SELL limit order fills only when market price reaches or exceeds limit price."""
        # Establish initial position: 10 AAPL @ $150
        database.execute_trade_atomic(self.user_id, "AAPL", "BUY", 10.0, 150.0)
        self.assertEqual(database.get_user_shares(self.user_id, "AAPL"), 10.0)

        # Place SELL limit order for 5 AAPL @ $170.0
        order_id = database.create_order(
            user_id=self.user_id,
            symbol="AAPL",
            side="SELL",
            order_type="LIMIT",
            product_type="CNC",
            quantity=5.0,
            price=170.0
        )

        # Market price is $165.0 (does not satisfy >= $170.0)
        database.upsert_market_cache({"symbol": "AAPL", "last_price": 165.0})
        fills = trading_engine.match_pending_orders(symbol="AAPL")
        self.assertEqual(len(fills), 0, "SELL limit must not execute below limit price")

        # Market price rises to $172.0 (satisfies >= $170.0)
        database.upsert_market_cache({"symbol": "AAPL", "last_price": 172.0})
        fills = trading_engine.match_pending_orders(symbol="AAPL")
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0]["filled_price"], 172.0)

        # Verify 5 shares remaining in portfolio
        self.assertEqual(database.get_user_shares(self.user_id, "AAPL"), 5.0)
        # Realized P&L: 5 * (172.0 - 150.0) = +$110.0
        self.assertEqual(fills[0]["realized_pnl"], 110.0)

    # -------------------------------------------------------------
    # EDGE CASE D: Multiple pending BUY orders cannot over-reserve cash
    # -------------------------------------------------------------
    def test_case_d_multiple_pending_buy_orders_cannot_over_reserve(self):
        """Multiple pending orders pool reservations and cannot exceed cash balance."""
        database.update_user_balance(self.user_id, 1000.0)

        # Order 1: 5 shares @ $100 = $500 (Leaves $500 buying power)
        ord1 = database.create_order(self.user_id, "STOCK1", "BUY", "LIMIT", "CNC", 5.0, 100.0)
        self.assertGreater(ord1, 0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 500.0)

        # Order 2: 4 shares @ $100 = $400 (Leaves $100 buying power)
        ord2 = database.create_order(self.user_id, "STOCK2", "BUY", "LIMIT", "CNC", 4.0, 100.0)
        self.assertGreater(ord2, 0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 100.0)

        # Order 3: 2 shares @ $100 = $200 (Requires $200, only $100 available) -> MUST FAIL
        with self.assertRaises(ValueError) as ctx:
            database.create_order(self.user_id, "STOCK3", "BUY", "LIMIT", "CNC", 2.0, 100.0)
        self.assertIn("Insufficient funds / buying power", str(ctx.exception))

        # Total reserved remains exactly $900
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 900.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 100.0)

    # -------------------------------------------------------------
    # EDGE CASE E: Insufficient buying power rejects order placement
    # -------------------------------------------------------------
    def test_case_e_insufficient_buying_power_rejects_placement(self):
        """API rejects order placement if required cash exceeds available buying power."""
        database.update_user_balance(self.user_id, 500.0)

        # Try to buy 10 GOOGL @ $100 ($1,000 required, only $500 available)
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "GOOGL",
            "side": "BUY",
            "order_type": "LIMIT",
            "product_type": "CNC",
            "quantity": 10.0,
            "price": 100.0
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("Insufficient funds", data["message"])

        # No order created
        orders = database.get_user_orders(self.user_id)
        self.assertEqual(len(orders), 0)

    # -------------------------------------------------------------
    # EDGE CASE F: Filled BUY order converts reservation into cash debit exactly once
    # -------------------------------------------------------------
    def test_case_f_filled_buy_converts_reservation_cleanly(self):
        """Order fill clears reservation and applies actual cash debit without double-counting."""
        database.update_user_balance(self.user_id, 2000.0)

        # Place order: 10 AMD @ $100 ($1,000 reserved)
        order_id = database.create_order(self.user_id, "AMD", "BUY", "LIMIT", "CNC", 10.0, 100.0)
        self.assertEqual(database.get_user_balance(self.user_id), 2000.0)
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 1000.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 1000.0)

        # Fill order at $95.0 ($950 actual cash debit)
        res = database.fill_order_atomic(order_id, execution_price=95.0)
        self.assertTrue(res["success"])

        # Cash balance is now $2000 - $950 = $1,050.0
        self.assertEqual(database.get_user_balance(self.user_id), 1050.0)
        # Reservation is cleared
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 0.0)
        # Buying power equals cash balance
        self.assertEqual(database.get_user_buying_power(self.user_id), 1050.0)

    # -------------------------------------------------------------
    # EDGE CASE G: Cancellation releases reserved buying power exactly once
    # -------------------------------------------------------------
    def test_case_g_cancellation_releases_reservation_exactly_once(self):
        """Cancelling an order restores available buying power exactly once."""
        database.update_user_balance(self.user_id, 5000.0)

        order_id = database.create_order(self.user_id, "TSLA", "BUY", "LIMIT", "CNC", 10.0, 200.0)  # $2000
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 2000.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 3000.0)

        # Cancel order
        success = database.cancel_order(order_id, self.user_id)
        self.assertTrue(success)

        # Buying power fully restored
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 0.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 5000.0)
        self.assertEqual(database.get_user_balance(self.user_id), 5000.0)

        # Repeated cancellation fails and does not alter balance
        second_cancel = database.cancel_order(order_id, self.user_id)
        self.assertFalse(second_cancel)
        self.assertEqual(database.get_user_buying_power(self.user_id), 5000.0)

    # -------------------------------------------------------------
    # EDGE CASE H: Expiration releases reserved buying power exactly once
    # -------------------------------------------------------------
    def test_case_h_expiration_releases_reservation_exactly_once(self):
        """Expiring a stale DAY order marks it EXPIRED and restores buying power."""
        database.update_user_balance(self.user_id, 4000.0)

        order_id = database.create_order(self.user_id, "META", "BUY", "LIMIT", "CNC", 5.0, 300.0, validity="DAY")
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 1500.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 2500.0)

        # Manually expire order
        success = database.expire_order(order_id)
        self.assertTrue(success)

        # Verify order status
        orders = database.get_user_orders(self.user_id)
        self.assertEqual(orders[0]["status"], "EXPIRED")

        # Buying power restored
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 0.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 4000.0)

    # -------------------------------------------------------------
    # EDGE CASE I: Repeated worker execution does not double-fill an order
    # -------------------------------------------------------------
    def test_case_i_repeated_matching_does_not_double_fill(self):
        """Calling match_pending_orders repeatedly fills an eligible order exactly once."""
        database.upsert_market_cache({"symbol": "NFLX", "last_price": 400.0})

        order_id = database.create_order(self.user_id, "NFLX", "BUY", "LIMIT", "CNC", 2.0, 410.0)

        # First matching run fills the order
        fills1 = trading_engine.match_pending_orders(symbol="NFLX")
        self.assertEqual(len(fills1), 1)
        self.assertEqual(fills1[0]["order_id"], order_id)

        # Second matching run finds no open orders to fill
        fills2 = trading_engine.match_pending_orders(symbol="NFLX")
        self.assertEqual(len(fills2), 0)

        # Third matching run
        fills3 = trading_engine.match_pending_orders(symbol="NFLX")
        self.assertEqual(len(fills3), 0)

        # Only 2 shares owned (not 4 or 6)
        self.assertEqual(database.get_user_shares(self.user_id, "NFLX"), 2.0)
        # Only 1 transaction in audit log
        txs = database.get_transactions_by_user(self.user_id)
        self.assertEqual(len(txs), 1)

    # -------------------------------------------------------------
    # EDGE CASE J: Concurrent order submissions cannot overspend buying power
    # -------------------------------------------------------------
    def test_case_j_concurrent_submissions_cannot_overspend(self):
        """Concurrent order creations under thread contention serialize and protect buying power."""
        database.update_user_balance(self.user_id, 1000.0)

        # 5 concurrent attempts to each reserve $400 (4 shares @ $100)
        # Total possible: 1000 // 400 = 2 orders maximum. 3 must fail!
        def submit_order(i):
            try:
                # Add tiny random jitter
                return database.create_order(
                    user_id=self.user_id,
                    symbol="CONC",
                    side="BUY",
                    order_type="LIMIT",
                    product_type="CNC",
                    quantity=4.0,
                    price=100.0
                )
            except ValueError:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(submit_order, range(5)))

        successful_orders = [r for r in results if r is not None]
        self.assertEqual(len(successful_orders), 2, "Only exactly 2 orders of $400 each could fit in $1,000")

        # Reserved cash must be exactly $800, buying power $200
        self.assertEqual(database.get_user_reserved_cash(self.user_id), 800.0)
        self.assertEqual(database.get_user_buying_power(self.user_id), 200.0)

    # -------------------------------------------------------------
    # EDGE CASE K: Fill and cancellation race cannot both succeed
    # -------------------------------------------------------------
    def test_case_k_fill_and_cancel_race_condition_safety(self):
        """When fill and cancel race against the same order, exactly one succeeds."""
        database.update_user_balance(self.user_id, 2000.0)
        order_id = database.create_order(self.user_id, "RACE", "BUY", "LIMIT", "CNC", 5.0, 100.0)

        def do_fill():
            return database.fill_order_atomic(order_id, 100.0)

        def do_cancel():
            return database.cancel_order(order_id, self.user_id)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_fill = executor.submit(do_fill)
            f_cancel = executor.submit(do_cancel)
            fill_res = f_fill.result()
            cancel_res = f_cancel.result()

        # Mutual exclusivity: If fill succeeded, cancel returned False. If cancel succeeded, fill returned False.
        if fill_res.get("success"):
            self.assertFalse(cancel_res, "Cancel must not succeed if fill won race")
            self.assertEqual(database.get_user_balance(self.user_id), 1500.0)
            self.assertEqual(database.get_user_shares(self.user_id, "RACE"), 5.0)
        else:
            self.assertTrue(cancel_res, "Cancel must succeed if fill lost race")
            self.assertEqual(database.get_user_balance(self.user_id), 2000.0)
            self.assertEqual(database.get_user_shares(self.user_id, "RACE"), 0.0)

    # -------------------------------------------------------------
    # EDGE CASE L: Missing or invalid market data does not trigger fill
    # -------------------------------------------------------------
    def test_case_l_invalid_market_data_defers_execution(self):
        """If market data returns 0 or fails, order is deferred and never filled with fabricated price."""
        # Symbol with no price cached and mock price returning 0.0
        order_id = database.create_order(self.user_id, "NODATA", "BUY", "LIMIT", "CNC", 10.0, 50.0)

        with unittest.mock.patch("trading_engine.get_current_price", return_value=0.0):
            fills = trading_engine.match_pending_orders(symbol="NODATA")
            self.assertEqual(len(fills), 0, "Must defer when price is 0.0")

        # Order remains OPEN
        orders = database.get_user_orders(self.user_id)
        self.assertEqual(orders[0]["status"], "OPEN")
        self.assertEqual(database.get_user_shares(self.user_id, "NODATA"), 0.0)

    # -------------------------------------------------------------
    # EDGE CASE M: Failed execution rolls back all related updates
    # -------------------------------------------------------------
    def test_case_m_failed_execution_rolls_back_cleanly(self):
        """An operational error during fill rolls back cash, holdings, and order state."""
        order_id = database.create_order(self.user_id, "ROLL", "BUY", "LIMIT", "CNC", 5.0, 100.0)

        # Corrupt execution price with NaN
        res = database.fill_order_atomic(order_id, execution_price=-50.0)
        self.assertFalse(res["success"])

        # State remains clean and OPEN
        orders = database.get_user_orders(self.user_id)
        self.assertEqual(orders[0]["status"], "OPEN")
        self.assertEqual(database.get_user_balance(self.user_id), 10000.0)
        self.assertEqual(database.get_user_shares(self.user_id, "ROLL"), 0.0)

    # -------------------------------------------------------------
    # EDGE CASE N: SELL orders cannot sell more shares than user owns
    # -------------------------------------------------------------
    def test_case_n_sell_orders_cannot_exceed_available_shares(self):
        """SELL limit orders cannot reserve or sell more shares than available in portfolio."""
        # Buy 10 INTC
        database.execute_trade_atomic(self.user_id, "INTC", "BUY", 10.0, 30.0)

        # Place pending SELL limit for 6 INTC
        ord1 = database.create_order(self.user_id, "INTC", "SELL", "LIMIT", "CNC", 6.0, 35.0)
        self.assertGreater(ord1, 0)
        self.assertEqual(database.get_user_available_shares(self.user_id, "INTC"), 4.0)

        # Attempt to place pending SELL limit for 5 INTC (only 4 available) -> MUST FAIL
        with self.assertRaises(ValueError) as ctx:
            database.create_order(self.user_id, "INTC", "SELL", "LIMIT", "CNC", 5.0, 35.0)
        self.assertIn("Insufficient shares", str(ctx.exception))

    # -------------------------------------------------------------
    # EDGE CASE O: WAC and Realized P&L remain correct after limit-order fills
    # -------------------------------------------------------------
    def test_case_o_wac_and_realized_pnl_after_limit_fills(self):
        """Multi-lot limit order fills maintain exact WAC basis and calculate realized P&L on sell."""
        # 1. First BUY limit fill: 10 XYZ @ $100 = $1,000
        ord1 = database.create_order(self.user_id, "XYZ", "BUY", "LIMIT", "CNC", 10.0, 100.0)
        database.fill_order_atomic(ord1, 100.0)

        # 2. Second BUY limit fill: 10 XYZ @ $200 = $2,000
        ord2 = database.create_order(self.user_id, "XYZ", "BUY", "LIMIT", "CNC", 10.0, 200.0)
        database.fill_order_atomic(ord2, 200.0)

        # Portfolio WAC: (1000 + 2000) / 20 = $150.0
        portfolio = database.get_user_portfolio(self.user_id)
        xyz_pos = next(p for p in portfolio if p["ticker"] == "XYZ")
        self.assertEqual(xyz_pos["shares"], 20.0)
        self.assertEqual(xyz_pos["avg_buy_price"], 150.0)

        # 3. SELL limit fill: 5 XYZ @ $220.0
        ord3 = database.create_order(self.user_id, "XYZ", "SELL", "LIMIT", "CNC", 5.0, 220.0)
        sell_res = database.fill_order_atomic(ord3, 220.0)

        # Realized profit: 5 * (220.0 - 150.0) = +$350.0
        self.assertEqual(sell_res["realized_pnl"], 350.0)

        # Remaining portfolio: 15 shares XYZ @ $150.0 WAC
        portfolio2 = database.get_user_portfolio(self.user_id)
        xyz_pos2 = next(p for p in portfolio2 if p["ticker"] == "XYZ")
        self.assertEqual(xyz_pos2["shares"], 15.0)
        self.assertEqual(xyz_pos2["avg_buy_price"], 150.0)

    # -------------------------------------------------------------
    # EDGE CASE P: Manual and bot order attribution remains correct
    # -------------------------------------------------------------
    def test_case_p_bot_attribution_preserved_on_order_fill(self):
        """Orders created with is_bot=True preserve bot flag in orders and transactions upon fill."""
        bot_ord = database.create_order(
            user_id=self.user_id,
            symbol="BOTSTK",
            side="BUY",
            order_type="LIMIT",
            product_type="CNC",
            quantity=5.0,
            price=50.0,
            is_bot=True
        )

        fill_res = database.fill_order_atomic(bot_ord, 50.0)
        self.assertTrue(fill_res["is_bot"])

        # Check transactions table
        txs = database.get_transactions_by_user(self.user_id)
        bot_tx = next(t for t in txs if t["ticker"] == "BOTSTK")
        self.assertEqual(bot_tx["is_bot"], 1)

    # -------------------------------------------------------------
    # EDGE CASE Q: Existing MARKET orders continue to behave correctly
    # -------------------------------------------------------------
    def test_case_q_market_orders_execute_instantly(self):
        """Standard MARKET orders via /api/trade and /api/orders continue to execute immediately."""
        database.upsert_market_cache({"symbol": "MKTSTK", "last_price": 50.0})

        res = self.client.post("/api/trade", headers=self.headers, json={
            "ticker": "MKTSTK",
            "action": "BUY",
            "shares": 10.0
        })
        self.assertEqual(res.status_code, 200)

        # Portfolio updated immediately
        self.assertEqual(database.get_user_shares(self.user_id, "MKTSTK"), 10.0)
        # Cash debited immediately ($10,000 - $500 = $9,500)
        self.assertEqual(database.get_user_balance(self.user_id), 9500.0)

    # -------------------------------------------------------------
    # EDGE CASE R: Fresh database initialization and repeated initialization remain safe
    # -------------------------------------------------------------
    def test_case_r_fresh_and_repeated_init_safe(self):
        """init_db creates tables and indexes safely and is idempotent."""
        fresh_tmp = tempfile.mkdtemp(prefix="fresh_init_")
        fresh_db = os.path.join(fresh_tmp, "fresh.db")
        os.environ["DATABASE_PATH"] = fresh_db
        from config import Config
        Config.DB_PATH = fresh_db

        try:
            # First initialization
            database.init_db()

            # Repeated initialization
            database.init_db()

            with database.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
                self.assertIsNotNone(c.fetchone())
        finally:
            try:
                import gc
                gc.collect()
                if os.path.exists(fresh_db):
                    os.remove(fresh_db)
                if os.path.exists(fresh_tmp):
                    import shutil
                    shutil.rmtree(fresh_tmp, ignore_errors=True)
            except Exception:
                pass

    # -------------------------------------------------------------
    # EDGE CASE S: Existing historical data remains intact
    # -------------------------------------------------------------
    def test_case_s_existing_historical_data_intact(self):
        """Pre-existing orders and transactions with NULL or default values are read cleanly."""
        with database.get_connection() as conn:
            c = conn.cursor()
            now = database.datetime.now(database.timezone.utc).isoformat()
            c.execute(
                """
                INSERT INTO orders (user_id, symbol, side, order_type, quantity, price, status, created_at, updated_at)
                VALUES (?, 'HIST', 'BUY', 'LIMIT', 10.0, 100.0, 'OPEN', ?, ?)
                """,
                (self.user_id, now, now)
            )
            hist_order_id = c.lastrowid
            conn.commit()

        # Buying power calculation accounts for pre-existing orders
        bp = database.get_user_buying_power(self.user_id)
        self.assertEqual(bp, 9000.0)  # 10,000 - (10 * 100)

        # Can cancel historical order cleanly
        success = database.cancel_order(hist_order_id, self.user_id)
        self.assertTrue(success)
        self.assertEqual(database.get_user_buying_power(self.user_id), 10000.0)


if __name__ == "__main__":
    unittest.main()
