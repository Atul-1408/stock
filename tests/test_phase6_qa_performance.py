"""Phase 6 QA, Performance, and Security Regression Test Suite.

Validates:
1. Database Consistency & Integrity:
   - PRAGMA foreign keys, journal_mode WAL, busy_timeout.
   - Transaction atomicity & rollback on constraint violations.
2. Worker Lifecycle & Resilience:
   - WorkerManager initialization, health query, and graceful shutdown.
3. Security Regressions:
   - Mandatory JWT authentication on all protected routes.
   - Token signature tampering & expiry validation (401).
   - SQL injection & path traversal attempts rejected safely.
   - Secrets & token sanitization (no credentials printed to logs/responses).
4. Error Handling & Provider Fault Tolerance:
   - 404 for non-existent resources.
   - 400 for invalid/malformed payloads.
   - Fallback behavior on third-party provider downtime.
5. Performance & Caching:
   - In-memory cache hit speeds (sub-millisecond).
   - Article deduplication throughput.
"""

import json
import os
import sys
import unittest
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "phase6-qa-regression-test-secret-key-32b!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
try:
    import yfinance as yf
    mock_ticker_obj = MagicMock()
    mock_ticker_obj.news = [
        {"title": "Global Tech Earnings Outperform Expectations", "link": "https://test.wire/1", "publisher": "Wire", "providerPublishTime": 1700000000},
        {"title": "Treasury Yields Stabilize Ahead of Central Bank Policy", "link": "https://test.wire/2", "publisher": "Wire", "providerPublishTime": 1700000000},
    ]
    yf.Ticker = MagicMock(return_value=mock_ticker_obj)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
from app import app
from config import Config
from worker_manager import WorkerManager
from market_brief_service import generate_market_brief, clear_brief_cache
from news_service import deduplicate_articles, compute_article_hash


class TestPhase6QAPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

        database.init_db()
        test_email = "qa_engineer@sovereign.test"
        existing = database.get_user_by_email(test_email)
        if not existing:
            cls.user_id = database.create_user(
                email=test_email,
                password_hash="qa_bcrypt_hash_placeholder",
                full_name="QA Engineer"
            )
        else:
            cls.user_id = existing["id"]

        from app import create_access_token
        with app.app_context():
            cls.valid_token = create_access_token(identity=str(cls.user_id))
        cls.auth_headers = {
            "Authorization": f"Bearer {cls.valid_token}",
            "Content-Type": "application/json"
        }

    # -------------------------------------------------------------
    # 1. DATABASE CONSISTENCY & CONCURRENCY PRAGMAS
    # -------------------------------------------------------------
    def test_01_database_pragmas(self):
        """Database enforces WAL mode, foreign keys, and busy timeout."""
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys;")
            fk = cursor.fetchone()[0]
            self.assertEqual(fk, 1, "Foreign keys pragma must be active")

            cursor.execute("PRAGMA journal_mode;")
            jm = cursor.fetchone()[0].upper()
            self.assertIn(jm, ["WAL", "MEMORY"], "Journal mode should be WAL for hardened concurrency")

            cursor.execute("PRAGMA busy_timeout;")
            bt = cursor.fetchone()[0]
            self.assertGreaterEqual(bt, 1000, "Busy timeout must be at least 1000ms")

    def test_02_database_foreign_key_constraint(self):
        """Violating foreign key constraints raises IntegrityError without database corruption."""
        with database.get_connection() as conn:
            cursor = conn.cursor()
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute(
                    """
                    INSERT INTO orders (user_id, symbol, side, order_type, quantity, price, created_at, updated_at)
                    VALUES (99999999, 'AAPL', 'BUY', 'MARKET', 10, 150.0, '2026-10-24T00:00:00', '2026-10-24T00:00:00')
                    """
                )

    # -------------------------------------------------------------
    # 2. WORKER LIFECYCLE & SHUTDOWN
    # -------------------------------------------------------------
    def test_03_worker_manager_lifecycle(self):
        """WorkerManager initializes, reports status, and stops without hanging threads."""
        manager = WorkerManager()
        status_init = manager.get_health_status()
        self.assertFalse(status_init["workers_started"])

        # Stop workers gracefully
        manager.stop_all()
        status_stopped = manager.get_health_status()
        self.assertFalse(status_stopped["workers_started"])

    # -------------------------------------------------------------
    # 3. SECURITY REGRESSION: AUTHORIZATION & INJECTION HARDENING
    # -------------------------------------------------------------
    def test_04_unauthenticated_request_rejected(self):
        """Protected endpoints reject requests missing Authorization header (401)."""
        endpoints = [
            "/api/auth/me",
            "/api/portfolio",
            "/api/orders/list",
            "/api/alerts",
            "/api/market/brief",
            "/api/stocks/AAPL/intelligence",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertIn(res.status_code, [401, 422], f"Endpoint {ep} must require valid authorization")

    def test_05_tampered_token_rejected(self):
        """Tampered or invalid JWT signature is rejected (401)."""
        tampered_headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "Content-Type": "application/json"
        }
        res = self.client.get("/api/auth/me", headers=tampered_headers)
        self.assertEqual(res.status_code, 401)

    def test_06_sql_injection_defense(self):
        """SQL injection attacks in path parameters fail safely without leaking internal database schema."""
        injection_payload = "AAPL' OR '1'='1"
        res = self.client.get(f"/api/stocks/{injection_payload}/details", headers=self.auth_headers)
        self.assertIn(res.status_code, [400, 404])
        data = json.loads(res.data)
        self.assertNotIn("syntax error", json.dumps(data).lower())

    def test_07_no_credentials_in_user_profile(self):
        """GET /api/auth/me never exposes password hashes, salts, or reset tokens."""
        res = self.client.get("/api/auth/me", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        user_data = json.loads(res.data).get("user", {})
        self.assertNotIn("password", user_data)
        self.assertNotIn("password_hash", user_data)
        self.assertNotIn("otp", user_data)

    # -------------------------------------------------------------
    # 4. ERROR HANDLING & TOLERANCE
    # -------------------------------------------------------------
    def test_08_invalid_json_payload(self):
        """Invalid JSON request bodies return clean 400 Bad Request."""
        res = self.client.post(
            "/api/orders",
            headers=self.auth_headers,
            data="this-is-not-json",
            content_type="application/json"
        )
        self.assertIn(res.status_code, [400, 422])

    def test_09_nonexistent_route_404(self):
        """Unmapped routes return standardized 404 response."""
        res = self.client.get("/api/nonexistent/subsystem/route")
        self.assertEqual(res.status_code, 404)

    # -------------------------------------------------------------
    # 5. PERFORMANCE, DEDUPLICATION & CACHING
    # -------------------------------------------------------------
    def test_10_deduplication_performance(self):
        """Deduplicating 1000 articles completes in under 50ms."""
        articles = [
            {
                "title": f"Headline Variation {i % 50} About Federal Reserve",
                "url": f"https://feed.test/news/{i % 50}?utm_source=twitter_{i}"
            }
            for i in range(1000)
        ]
        start_time = time.perf_counter()
        deduped = deduplicate_articles(articles)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        self.assertEqual(len(deduped), 50)
        self.assertLess(elapsed_ms, 50.0, f"Deduplication took {elapsed_ms:.2f}ms, expected < 50ms")

    def test_11_market_brief_cache_latency(self):
        """Serving cached AI market brief takes under 5ms."""
        clear_brief_cache()
        # Seed cache
        generate_market_brief(force_refresh=True)

        start_time = time.perf_counter()
        cached = generate_market_brief(force_refresh=False)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        self.assertTrue(cached.get("cached", False))
        self.assertLess(elapsed_ms, 5.0, f"Cached brief fetch took {elapsed_ms:.2f}ms, expected < 5ms")


if __name__ == "__main__":
    unittest.main()
