"""WSGI Production Entry Point for Sovereign Intelligence.

Compatible with production WSGI servers:
  Linux / Containers: gunicorn -w 2 -b 0.0.0.0:5000 --timeout 60 wsgi:app
  Windows Server:     waitress-serve --port=5000 wsgi:app
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
