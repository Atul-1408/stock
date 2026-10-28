# AUDIT 03: Market Data and Finnhub Integration Audit

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Audit Date:** 2026-10-28  
**Auditor:** Senior Financial Systems QA Engineer  
**Status:** AUDIT ONLY (Read-Only Inspection)

---

## 1. Market Data Pipeline Traced

```text
External Providers (Finnhub API / yfinance)
      │
      ▼
Backend Ingest Service ([src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py) / [src/price_fetcher.py](file:///c:/Users/Atul/project/stock-main/src/price_fetcher.py) / [src/market_data_feed.py](file:///c:/Users/Atul/project/stock-main/src/market_data_feed.py))
      │
      ▼
Persistence & Cache (`market_data_cache`, `prices`, `market_indices` in SQLite)
      │
      ▼
Flask API Endpoints (`/api/ticker-tape`, `/api/prices/<ticker>`, `/api/market/watch`, `/api/market/indices`)
      │
      ▼
Frontend API Clients ([frontend/src/services/TickerService.js](file:///c:/Users/Atul/project/stock-main/frontend/src/services/TickerService.js) / [frontend/src/utils/api.js](file:///c:/Users/Atul/project/stock-main/frontend/src/utils/api.js))
      │
      ▼
UI Components ([TickerTape.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/TickerTape.jsx), [PriceChart.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/PriceChart.jsx), [MarketWatch.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/MarketWatch.jsx))
```

---

## 2. Finnhub Integration Investigation

### Configuration & Key Ingestion
- Configured in [.env](file:///c:/Users/Atul/project/stock-main/.env) as `FINNHUB_API_KEY`.
- Loaded via `Config.FINNHUB_API_KEY` and `os.getenv('FINNHUB_API_KEY', '')`.
- Live API probe test confirmed the key is valid (HTTP 200, returned live AAPL quote and 100 news items).

### Quote Endpoint (`/v1/quote`)
- **Usage:** Used only in [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L284-L313) for `/api/ticker-tape`.
- **Sequential Fetching Defect:** Executes synchronous `requests.get` inside a sequential `for ticker in ticker_list` loop:
  ```python
  for ticker in ticker_list:
      ...
      r = req.get('https://finnhub.io/api/v1/quote', params={'symbol': finnhub_symbol, 'token': finnhub_key}, timeout=6)
  ```
  - For 15 tickers, this generates 15 sequential HTTP connections.
  - Finnhub Free Tier allows **60 API calls per minute**.
  - A single request with 15 tickers consumes 25% of the entire minute's quota. Two rapid refreshes trigger HTTP 429 Rate Limit errors.
- **Symbol Support:**
  - Indian symbols (`.NS`, `.BO`) explicitly return `None` from `_to_finnhub_symbol` and are skipped, falling back to yfinance.
  - Crypto symbols (e.g. `BTC-USD`) are mapped to `BINANCE:BTCUSDT`.
  - US symbols pass through directly (`AAPL`, `MSFT`, `NVDA`).

### Historical Prices
- **Finnhub Usage:** **NONE.** Finnhub is not used for historical OHLCV data anywhere in the codebase.
- **Provider:** All historical data is fetched via Yahoo Finance in [src/price_fetcher.py](file:///c:/Users/Atul/project/stock-main/src/price_fetcher.py#L16) and [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L791).

---

## 3. Market Data Cache & Stock Universe Findings

### Defect 1: Unseeded Stock Universe & Cold Cache Starvation
- **File / Location:** [src/database.py](file:///c:/Users/Atul/project/stock-main/src/database.py) & [src/market_data_feed.py](file:///c:/Users/Atul/project/stock-main/src/market_data_feed.py#L143-L148)
- **Code:**
  ```python
  def _get_cached_symbols(self):
      with get_connection() as conn:
          cursor = conn.cursor()
          cursor.execute("SELECT symbol FROM market_data_cache LIMIT 100")
          return [row['symbol'] for row in cursor.fetchall()]
  ```
- **Actual State:**
  - Active SQLite database has only **1 row** in `stock_universe` (`AAPL`).
  - Active SQLite database has only **2 rows** in `market_data_cache` (`AAPL`, `RELIANCE.NS`).
  - Because `MarketDataFeed` only polls symbols that already exist in `market_data_cache`, it never discovers or populates other tracked stocks.
  - The stock importer script [src/stock_data_importer.py](file:///c:/Users/Atul/project/stock-main/src/stock_data_importer.py) contains 100+ US and Indian stocks but is never invoked automatically on application startup.
- **User Impact:** When a user opens [frontend/src/pages/MarketWatch.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/MarketWatch.jsx), the institutional market scanner displays only 1 stock (AAPL) instead of the full stock universe.
- **Severity:** P1 (Core Functionality Empty)
- **Status:** CONFIRMED BUG

---

### Defect 2: Misleading "LIVE" Badges on Stale or Closed Market Data
- **File / Location:** [frontend/src/pages/Dashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/Dashboard.jsx#L132)
- **Code:**
  ```jsx
  <span className="font-bold text-slate-300">{idx.display_name || idx.index_name}</span>
  <span className="text-[9px] text-slate-500">LIVE</span>
  ```
- **Actual Behavior:** The UI hardcodes the text `"LIVE"` next to all index values and tickers regardless of whether the market is open, closed, or whether data was served from a stale local cache.
- **Expected Behavior:** Display freshness indicators (e.g. "LIVE", "DELAYED", "CLOSED") based on `last_trade_time` or market exchange hours.
- **Severity:** P3 (UI Polish / Data Honesty)
- **Status:** CONFIRMED BUG

---

## 4. Summary of Phase 3 Findings

| ID | Finding | Severity | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| **MKT-01** | `stock_universe` unseeded (only 1 row exists in production DB) | High | P1 | CONFIRMED BUG |
| **MKT-02** | `MarketDataFeed` circular cold-start starvation | High | P1 | CONFIRMED BUG |
| **MKT-03** | Finnhub quotes fetched via sequential loop risking 429 rate limit | Medium | P2 | CONFIRMED BUG |
| **MKT-04** | Finnhub is not used for historical prices (yfinance only) | Low | P3 | VERIFIED WORKING (AS DESIGNED) |
| **MKT-05** | UI hardcodes "LIVE" label on closed or cached data | Low | P3 | CONFIRMED BUG |
