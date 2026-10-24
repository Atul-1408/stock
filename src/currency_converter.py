"""Currency Converter — handles multi-currency conversion with live exchange rates.

Uses exchangerate-api.com (free, no API key needed) for rate updates.
Caches rates in-memory and in SQLite for fast conversions.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import threading
import time
import requests
from datetime import datetime, timezone

import database


class CurrencyConverter:
    """In-memory currency conversion engine backed by SQLite."""

    def __init__(self):
        self.cache = {}  # {from_to: rate}
        self.symbols = {}  # {code: symbol}
        self._load_cache()

    def _load_cache(self):
        """Load exchange rates and symbols into memory from DB."""
        try:
            with database.get_connection() as conn:
                cursor = conn.cursor()
                # Load rates
                cursor.execute("SELECT from_currency, to_currency, rate FROM exchange_rates")
                for row in cursor.fetchall():
                    key = f"{row['from_currency']}_{row['to_currency']}"
                    self.cache[key] = float(row['rate'])

                # Load symbols
                cursor.execute("SELECT code, symbol FROM currencies WHERE is_active = 1")
                for row in cursor.fetchall():
                    self.symbols[row['code']] = row['symbol']
        except Exception as e:
            print(f"[CurrencyConverter] Cache load error: {e}")

    def convert(self, amount, from_currency, to_currency):
        """Convert amount between currencies. Uses triangular conversion via USD if needed."""
        if amount is None:
            return None
        if from_currency == to_currency:
            return amount

        amount = float(amount)

        # Direct rate
        key = f"{from_currency}_{to_currency}"
        if key in self.cache:
            return amount * self.cache[key]

        # Reverse rate
        rev = f"{to_currency}_{from_currency}"
        if rev in self.cache and self.cache[rev] != 0:
            return amount / self.cache[rev]

        # Triangular via USD
        usd_amount = amount
        if from_currency != 'USD':
            from_key = f"USD_{from_currency}"
            if from_key in self.cache and self.cache[from_key] != 0:
                usd_amount = amount / self.cache[from_key]
            else:
                from_rev = f"{from_currency}_USD"
                if from_rev in self.cache:
                    usd_amount = amount * self.cache[from_rev]
                else:
                    return amount  # Can't convert, return original

        if to_currency == 'USD':
            return usd_amount

        to_key = f"USD_{to_currency}"
        if to_key in self.cache:
            return usd_amount * self.cache[to_key]

        return amount  # Fallback

    def get_rate(self, from_currency, to_currency):
        """Get the exchange rate between two currencies."""
        if from_currency == to_currency:
            return 1.0
        key = f"{from_currency}_{to_currency}"
        if key in self.cache:
            return self.cache[key]
        rev = f"{to_currency}_{from_currency}"
        if rev in self.cache and self.cache[rev] != 0:
            return 1.0 / self.cache[rev]
        return None

    def get_symbol(self, currency_code):
        """Get the symbol for a currency code."""
        return self.symbols.get(currency_code, currency_code)

    def format_currency(self, amount, currency_code):
        """Format amount with proper currency symbol. Indian format for INR."""
        if amount is None:
            return '—'
        symbol = self.get_symbol(currency_code)
        amount = float(amount)

        if currency_code == 'INR':
            return f"{symbol}{self._indian_format(amount)}"
        elif currency_code == 'JPY':
            return f"{symbol}{amount:,.0f}"
        else:
            return f"{symbol}{amount:,.2f}"

    def _indian_format(self, amount):
        """Format number in Indian style (xx,xx,xxx.xx)."""
        negative = amount < 0
        amount = abs(amount)
        s = f"{amount:.2f}"
        rupees, paise = s.split('.')

        if len(rupees) > 3:
            last3 = rupees[-3:]
            rest = rupees[:-3]
            groups = []
            while rest:
                groups.insert(0, rest[-2:])
                rest = rest[:-2]
            formatted = ','.join(groups) + ',' + last3
        else:
            formatted = rupees

        result = f"{formatted}.{paise}"
        return f"-{result}" if negative else result

    def update_rates_from_api(self):
        """Fetch latest exchange rates from free API and update DB + cache."""
        print("[CurrencyConverter] Updating exchange rates...")
        try:
            resp = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=10)
            if resp.status_code != 200:
                print(f"[CurrencyConverter] API returned {resp.status_code}")
                return

            rates = resp.json().get('rates', {})
            now = datetime.now(timezone.utc).isoformat()

            with database.get_connection() as conn:
                cursor = conn.cursor()
                for code, rate in rates.items():
                    cursor.execute(
                        """INSERT INTO exchange_rates (from_currency, to_currency, rate, updated_at)
                           VALUES ('USD', ?, ?, ?)
                           ON CONFLICT(from_currency, to_currency) DO UPDATE SET rate=excluded.rate, updated_at=excluded.updated_at""",
                        (code, rate, now)
                    )
                conn.commit()

            self._load_cache()
            print(f"[CurrencyConverter] Updated {len(rates)} exchange rates")

        except Exception as e:
            print(f"[CurrencyConverter] Rate update error: {e}")

    def start_auto_update(self, interval_seconds=3600):
        """Start background thread to update rates hourly."""
        def loop():
            self.update_rates_from_api()  # Immediate first update
            while True:
                time.sleep(interval_seconds)
                self.update_rates_from_api()

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        print("[CurrencyConverter] Auto-update started (hourly)")


# Singleton
currency_converter = CurrencyConverter()
