import sqlite3
import os

db_path = 'data/stock_dashboard.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== TABLES ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row['name'] for row in cursor.fetchall()]
for table in tables:
    print(f"\nTable: {table}")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col['name']} ({col['type']})")

conn.close()
