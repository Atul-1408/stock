"""Pytest Root Configuration and Database Isolation Fixture.

Guarantees that all test suites execute against an isolated temporary SQLite database,
preventing any contamination, mutation, or pollution of the user's active database
(data/stock_dashboard.db).
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest

# Ensure project root and src/ are in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "src") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "src"))

# Create temporary directory for the isolated test database
_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="sovereign_test_session_")
_TEST_DB_PATH = Path(_TEST_TEMP_DIR) / "test_stock_dashboard.db"

# Force test environment variables before local modules are imported
os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["DATABASE_PATH"] = str(_TEST_DB_PATH)
os.environ["DB_PATH"] = str(_TEST_DB_PATH)
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["JWT_SECRET_KEY"] = "test-session-isolated-jwt-secret-key-32b!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# Initialize Config with isolated database path
from config import Config
Config.DB_PATH = _TEST_DB_PATH
Config.IS_PRODUCTION = False

import database
database.init_db()


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """Session-scoped fixture guaranteeing tests only touch the temporary database."""
    Config.DB_PATH = _TEST_DB_PATH
    yield _TEST_DB_PATH
    # Cleanup temporary database directory after all tests finish
    shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)
