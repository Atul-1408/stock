import sqlite3
import sys
from pathlib import Path

# Mock Config for simple test
class Config:
    DB_PATH = Path("data/stock_dashboard.db")

def test_db():
    print(f"Testing DB at {Config.DB_PATH}")
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        row = cursor.fetchone()
        print(f"Users count: {row['count']}")
        
        # Check currencies
        cursor.execute("SELECT COUNT(*) as count FROM currencies")
        row = cursor.fetchone()
        print(f"Currencies count: {row['count']}")
        
        conn.close()
        print("DB test PASSED")
    except Exception as e:
        print(f"DB test FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_db()
