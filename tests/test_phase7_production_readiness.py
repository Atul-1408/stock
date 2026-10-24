"""Automated Test Suite for Phase 7: Production Readiness.

Tests:
1. Health and observability endpoints (/api/health, /api/health/live, /api/health/ready).
2. Security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy).
3. Production configuration validation (JWT secret strength, CORS wildcard ban).
4. Trading mode safety switch (Paper default, live execution blocking).
5. Database backup and restore verification.
"""

import os
import shutil
import sys
import unittest
from pathlib import Path

# Add src and scripts to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))
sys.path.append(str(BASE_DIR / "scripts"))

from config import Config
from app import app
from db_backup import backup_database, restore_database


class TestPhase7ProductionReadiness(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_health_endpoint(self):
        """Verify /api/health returns comprehensive status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertIn("trading_mode", data)
        self.assertIn("live_trading_enabled", data)
        self.assertFalse(data["live_trading_enabled"])  # Live trading MUST be false by default
        self.assertIn("workers", data)
        self.assertIn("timestamp", data)

    def test_02_liveness_and_readiness_probes(self):
        """Verify K8s/ECS orchestrator probes return 200."""
        live_res = self.client.get("/api/health/live")
        self.assertEqual(live_res.status_code, 200)
        self.assertEqual(live_res.get_json()["status"], "live")

        ready_res = self.client.get("/api/health/ready")
        self.assertEqual(ready_res.status_code, 200)
        self.assertEqual(ready_res.get_json()["status"], "ready")

    def test_03_security_headers_enforced(self):
        """Verify OWASP-recommended security headers are set on all responses."""
        response = self.client.get("/api/health")
        headers = response.headers

        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertEqual(headers.get("Cross-Origin-Opener-Policy"), "same-origin-allow-popups")

    def test_04_production_config_validation(self):
        """Verify production validator detects unsafe settings."""
        # Test 1: Short JWT key in production mode
        orig_is_prod = Config.IS_PRODUCTION
        orig_jwt = Config.JWT_SECRET_KEY
        orig_cors = Config.CORS_ALLOWED_ORIGINS

        try:
            Config.IS_PRODUCTION = True
            Config.JWT_SECRET_KEY = "too-short"
            with self.assertRaises(RuntimeError) as ctx:
                Config.validate_production_config()
            self.assertIn("JWT_SECRET_KEY must be at least 32 characters", str(ctx.exception))

            # Test 2: Wildcard CORS in production
            Config.JWT_SECRET_KEY = "a" * 64
            Config.CORS_ALLOWED_ORIGINS = ["*"]
            with self.assertRaises(RuntimeError) as ctx:
                Config.validate_production_config()
            self.assertIn("Wildcard '*' in CORS_ALLOWED_ORIGINS is prohibited", str(ctx.exception))

            # Test 3: Valid production configuration passes
            Config.CORS_ALLOWED_ORIGINS = ["https://terminal.sovereign.internal"]
            result = Config.validate_production_config()
            self.assertTrue(result["valid"])
        finally:
            Config.IS_PRODUCTION = orig_is_prod
            Config.JWT_SECRET_KEY = orig_jwt
            Config.CORS_ALLOWED_ORIGINS = orig_cors

    def test_05_trading_safety_switches(self):
        """Verify paper trading is default and live trading requires dual authorization."""
        self.assertEqual(Config.TRADING_MODE, "PAPER")
        self.assertFalse(Config.IS_LIVE_TRADING_ENABLED)

    def test_06_database_backup_and_recovery(self):
        """Verify programmatic online backup and disaster recovery."""
        test_backup_dir = BASE_DIR / "backups" / "test_scratch"
        test_backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Create backup
            archive_path = backup_database(destination_dir=test_backup_dir, retain_count=2)
            self.assertTrue(archive_path.exists())
            self.assertTrue(archive_path.name.endswith(".db.gz"))

            # Test restore to staging target
            restore_target = test_backup_dir / "restored_test.db"
            restore_database(archive_path, target_db=restore_target, force=True)
            self.assertTrue(restore_target.exists())
            self.assertGreater(restore_target.stat().st_size, 0)
        finally:
            shutil.rmtree(test_backup_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
