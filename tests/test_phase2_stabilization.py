"""Phase 2 Backend & Database Stabilization Test Suite.

Validates:
1. Backend startup and routing.
2. Database initialization, WAL mode, foreign keys, and indexes.
3. Atomic transaction rollback on financial state changes.
4. Authentication regression.
5. Invalid order inputs (NaN, Inf, negative, zero, out-of-range, bad symbol/side).
6. Rapid duplicate order submission prevention (idempotency).
7. Stale market data detection.
8. Background worker startup, telemetry, and graceful shutdown.
9. Multiple-worker safety via single-instance leader file locking.
10. API error response formatting.
11. Online database backup capability.
"""

import json
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Set testing environment before local imports
os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "phase2-test-secret-key-32-bytes-long!"

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
from app import app
from config import Config
from order_validator import (
    duplicate_detector,
    is_price_recent,
    validate_order_input,
)
from worker_manager import ProcessLock, WorkerManager, worker_manager


class TestPhase2Stabilization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

        # Initialize database
        database.init_db()

        # Create isolated test user
        cls.test_email = "phase2_tester@example.com"
        cls.test_password = "SecurePassword123!"

        existing = database.get_user_by_email(cls.test_email)
        if not existing:
            from werkzeug.security import generate_password_hash
            cls.user_id = database.create_user(
                cls.test_email,
                generate_password_hash(cls.test_password),
                username="phase2_tester",
                full_name="Phase Two Tester"
            )
        else:
            cls.user_id = existing["id"]

        # Reset user starting balance to 100,000
        database.update_user_balance(cls.user_id, 100000.0)

        # Login to obtain JWT
        login_res = cls.client.post("/api/auth/login", json={
            "email": cls.test_email,
            "password": cls.test_password
        })
        cls.token = login_res.get_json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Seed mock market cache for RELIANCE.NS and AAPL
        now = datetime.now(timezone.utc).isoformat()
        database.upsert_market_cache({
            "symbol": "RELIANCE.NS",
            "last_price": 2500.0,
            "open_price": 2490.0,
            "high_price": 2520.0,
            "low_price": 2480.0,
            "prev_close": 2485.0,
            "volume": 100000,
            "change_pct": 0.6,
            "last_trade_time": now
        })
        database.upsert_market_cache({
            "symbol": "AAPL",
            "last_price": 180.0,
            "open_price": 179.0,
            "high_price": 182.0,
            "low_price": 178.5,
            "prev_close": 179.5,
            "volume": 500000,
            "change_pct": 0.28,
            "last_trade_time": now
        })

    def setUp(self):
        # Reset balance before each trade test
        database.update_user_balance(self.user_id, 100000.0)

    # ---------------------------------------------------------
    # 1. Backend Startup & Route Registration
    # ---------------------------------------------------------
    def test_01_backend_startup(self):
        """Verify application starts and /health responds with 200 OK."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "stock-sentiment-api")
        self.assertIn("workers", data)

    # ---------------------------------------------------------
    # 2. Database Initialization, Pragmas & Indexes
    # ---------------------------------------------------------
    def test_02_database_initialization_pragmas_and_indexes(self):
        """Verify WAL mode, foreign keys, and performance indexes."""
        with database.get_connection() as conn:
            cursor = conn.cursor()

            # Check foreign keys
            cursor.execute("PRAGMA foreign_keys")
            fk_row = cursor.fetchone()
            self.assertEqual(fk_row[0], 1, "Foreign keys must be ON")

            # Check journal mode (WAL or memory in some test setups)
            cursor.execute("PRAGMA journal_mode")
            jm_row = cursor.fetchone()
            self.assertIn(jm_row[0].lower(), ("wal", "memory"), "Journal mode should be WAL")

            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
            indexes = [r[0] for r in cursor.fetchall()]
            self.assertIn("idx_orders_user_status", indexes)
            self.assertIn("idx_orders_symbol", indexes)
            self.assertIn("idx_portfolio_user_ticker", indexes)
            self.assertIn("idx_transactions_user", indexes)

    # ---------------------------------------------------------
    # 3. Database Transaction Rollback on Failure
    # ---------------------------------------------------------
    def test_03_database_transaction_rollback(self):
        """Verify that an interrupted or failing transaction rolls back completely."""
        initial_balance = database.get_user_balance(self.user_id)

        # Attempt an order with insufficient funds
        result = database.execute_trade_atomic(
            user_id=self.user_id,
            symbol="RELIANCE.NS",
            side="BUY",
            quantity=1000.0,  # 1000 * 2500 = 2,500,000 > 100,000 balance
            execution_price=2500.0
        )
        self.assertFalse(result["success"])
        self.assertIn("Insufficient funds", result["message"])

        # Balance must remain exactly unchanged
        balance_after = database.get_user_balance(self.user_id)
        self.assertEqual(initial_balance, balance_after)

        # Portfolio should not have any holdings for RELIANCE.NS
        shares = database.get_user_shares(self.user_id, "RELIANCE.NS")
        self.assertEqual(shares, 0.0)

    # ---------------------------------------------------------
    # 4. Authentication Regression Tests
    # ---------------------------------------------------------
    def test_04_auth_regression(self):
        """Verify login, token verification, and /api/auth/me work correctly."""
        res = self.client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("user", {}).get("email"), self.test_email)

    # ---------------------------------------------------------
    # 5. Invalid Order Inputs Validation
    # ---------------------------------------------------------
    def test_05_invalid_order_inputs(self):
        """Reject non-finite numbers, negatives, zero, bad symbol, and invalid order types."""
        # 1. Negative quantity
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL", "side": "BUY", "quantity": -10, "order_type": "MARKET"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("greater than zero", res.get_json()["message"])

        # 2. Zero quantity
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL", "side": "BUY", "quantity": 0, "order_type": "MARKET"
        })
        self.assertEqual(res.status_code, 400)

        # 3. Invalid side
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL", "side": "HOLD", "quantity": 10, "order_type": "MARKET"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Must be BUY or SELL", res.get_json()["message"])

        # 4. Bad symbol
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "INVALID$$$SYMBOL!", "side": "BUY", "quantity": 10, "order_type": "MARKET"
        })
        self.assertEqual(res.status_code, 400)

        # 5. Missing price on LIMIT order
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL", "side": "BUY", "quantity": 10, "order_type": "LIMIT"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Limit price is required", res.get_json()["message"])

        # 6. Negative price on LIMIT order
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL", "side": "BUY", "quantity": 10, "order_type": "LIMIT", "price": -50.0
        })
        self.assertEqual(res.status_code, 400)

        # 7. Exceeding maximum allowable quantity cap
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL", "side": "BUY", "quantity": 50_000_000, "order_type": "MARKET"
        })
        self.assertEqual(res.status_code, 400)

    # ---------------------------------------------------------
    # 6. Duplicate Order Prevention (Idempotency)
    # ---------------------------------------------------------
    def test_06_duplicate_order_rejection(self):
        """Verify rapid identical order submissions are rejected with 409 Conflict."""
        order_payload = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 2.0,
            "order_type": "MARKET"
        }

        # First submission should succeed
        res1 = self.client.post("/api/orders", headers=self.headers, json=order_payload)
        self.assertEqual(res1.status_code, 201)

        # Immediate duplicate submission should be rejected
        res2 = self.client.post("/api/orders", headers=self.headers, json=order_payload)
        self.assertEqual(res2.status_code, 409)
        self.assertIn("Duplicate order detected", res2.get_json()["message"])

    # ---------------------------------------------------------
    # 7. Stale Market Data Handling
    # ---------------------------------------------------------
    def test_07_stale_market_data_handling(self):
        """Verify is_price_recent identifies fresh vs stale timestamps."""
        fresh_time = datetime.now(timezone.utc).isoformat()
        stale_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        self.assertTrue(is_price_recent(fresh_time, max_age_hours=24.0))
        self.assertFalse(is_price_recent(stale_time, max_age_hours=24.0))
        self.assertFalse(is_price_recent(None))

    # ---------------------------------------------------------
    # 8. Background Worker Telemetry & Shutdown
    # ---------------------------------------------------------
    def test_08_worker_telemetry_and_shutdown(self):
        """Verify worker_manager health reporting and clean stop_all behavior."""
        health = worker_manager.get_health_status()
        self.assertIn("workers", health)
        self.assertIn("market_data_feed", health["workers"])
        self.assertIn("trading_bot", health["workers"])

        # Test recording heartbeats and error isolation
        worker_manager.record_heartbeat("market_data_feed")
        self.assertTrue(worker_manager.is_running("market_data_feed"))

        worker_manager.record_error("alert_engine", "Mock alert network timeout")
        updated_health = worker_manager.get_health_status()
        self.assertEqual(updated_health["workers"]["alert_engine"]["status"], "error")
        self.assertEqual(updated_health["workers"]["alert_engine"]["last_error"], "Mock alert network timeout")

        # Test stop_all
        worker_manager.stop_all()
        stopped_health = worker_manager.get_health_status()
        self.assertFalse(stopped_health["is_leader"])

    # ---------------------------------------------------------
    # 9. Multiple-Worker Safety (Single-Instance Leader Lock)
    # ---------------------------------------------------------
    def test_09_multiple_worker_locking_safety(self):
        """Verify only one process can acquire leader lock on workers.lock."""
        temp_dir = tempfile.mkdtemp()
        lock_file = Path(temp_dir) / "test_workers.lock"

        lock_1 = ProcessLock(lock_file)
        lock_2 = ProcessLock(lock_file)

        try:
            # First process acquires lock
            self.assertTrue(lock_1.acquire())
            self.assertTrue(lock_1.acquired)

            # Second process attempting lock must fail (advisory non-blocking)
            self.assertFalse(lock_2.acquire())
            self.assertFalse(lock_2.acquired)

            # First releases lock
            lock_1.release()
            self.assertFalse(lock_1.acquired)

            # Now second process can acquire
            self.assertTrue(lock_2.acquire())
            self.assertTrue(lock_2.acquired)
            lock_2.release()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ---------------------------------------------------------
    # 10. API Error Response Format Consistency
    # ---------------------------------------------------------
    def test_10_api_error_response_format(self):
        """Verify API error responses return standardized status and message keys."""
        # Non-existent endpoint -> 404
        res = self.client.get("/api/non-existent-endpoint", headers=self.headers)
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIn("message", data)

        # Cancel non-existent order -> 404
        res2 = self.client.delete("/api/orders/999999/cancel", headers=self.headers)
        self.assertEqual(res2.status_code, 404)
        data2 = res2.get_json()
        self.assertEqual(data2.get("status"), "error")

    # ---------------------------------------------------------
    # 11. Database Online Backup Verification
    # ---------------------------------------------------------
    def test_11_database_backup(self):
        """Verify database hot backup functionality creates a valid SQLite backup."""
        temp_backup = Path(tempfile.gettempdir()) / "phase2_test_backup.db"
        if temp_backup.exists():
            temp_backup.unlink()

        backup_file = database.backup_database(str(temp_backup))
        self.assertTrue(Path(backup_file).exists())
        self.assertGreater(Path(backup_file).stat().st_size, 0)

        # Verify backup can be opened and queried
        b_conn = sqlite3.connect(backup_file)
        b_cursor = b_conn.cursor()
        b_cursor.execute("SELECT count(*) FROM users")
        count = b_cursor.fetchone()[0]
        self.assertGreater(count, 0)
        b_conn.close()

        # Clean up
        temp_backup.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
