# AUDIT 02: Backend Architecture and API Audit

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Audit Date:** 2026-10-28  
**Auditor:** Senior Software Architect & Python Backend Engineer  
**Status:** AUDIT ONLY (Read-Only Inspection)

---

## 1. Architecture Overview

The backend is built with Python 3.10+ and Flask 3.1.2, serving a RESTful JSON API.
- **Entry point:** [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py) & [wsgi.py](file:///c:/Users/Atul/project/stock-main/wsgi.py)
- **Configuration:** [src/config.py](file:///c:/Users/Atul/project/stock-main/src/config.py)
- **Database Layer:** [src/database.py](file:///c:/Users/Atul/project/stock-main/src/database.py) (SQLite with WAL mode and row factory)
- **Worker Management:** [src/worker_manager.py](file:///c:/Users/Atul/project/stock-main/src/worker_manager.py) (advisory file locking via `ProcessLock`)
- **Intelligence Services:** [src/news_service.py](file:///c:/Users/Atul/project/stock-main/src/news_service.py), [src/sentiment_service.py](file:///c:/Users/Atul/project/stock-main/src/sentiment_service.py), [src/chatbot_engine.py](file:///c:/Users/Atul/project/stock-main/src/chatbot_engine.py)

---

## 2. In-Depth Backend Findings & Defects

### Defect 1: Single-Entry Ticker Cache Collision
- **File / Location:** [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L158-L163) & [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L214-L218)
- **Code:**
  ```python
  _ticker_tape_cache = {
      "ts": 0.0,
      "key": None,
      "payload": None,
  }
  ...
  if (
      _ticker_tape_cache.get("payload") is not None
      and _ticker_tape_cache.get("key") == cache_key
      and (now_ts - float(_ticker_tape_cache.get("ts") or 0.0)) < 15.0
  ):
      return jsonify(_ticker_tape_cache["payload"]), 200
  ```
- **Reproduction Conditions:** Frontend `TickerService.js` batches requests into chunks of 10 tickers (e.g. Batch 1 = 10 tickers, Batch 2 = 8 tickers).
- **Actual Behavior:** Batch 1 arrives, fetches prices, and writes `_ticker_tape_cache["key"] = "AAPL,AMZN,..."`. 100ms later, Batch 2 arrives, fetches prices, and overwrites `_ticker_tape_cache["key"] = "ADANIENT.NS,..."`. On the subsequent 15s polling cycle, Batch 1 misses cache because `key` is Batch 2. Both batches miss cache 100% of the time, causing continuous redundant upstream calls.
- **Expected Behavior:** Cache should be keyed by `cache_key` (a `dict` or LRU cache with expiration timestamps) so independent batches remain cached.
- **Severity:** P2 (High Reliability / Latency Impact)
- **Status:** CONFIRMED BUG

---

### Defect 2: Sequential Blocking Price Calls in Portfolio Valuation
- **File / Location:** [src/trading_engine.py](file:///c:/Users/Atul/project/stock-main/src/trading_engine.py#L75-L112)
- **Code:**
  ```python
  def get_portfolio_summary(user_id: int):
      portfolio = get_user_portfolio(user_id)
      ...
      for holding in portfolio:
          ticker = holding['ticker']
          ...
          current_price = get_current_price(ticker)
          market_value = shares * current_price
          pnl = market_value - total_invested
  ```
- **Reproduction Conditions:** User has $N$ open positions in their portfolio.
- **Actual Behavior:** Calls `get_current_price(ticker)` sequentially inside the loop, issuing $N$ individual network requests to Yahoo Finance on every portfolio request. If one request fails or times out, `get_current_price` returns `0.0`, resulting in `market_value = 0` and `pnl = -total_invested` (-100% loss).
- **Expected Behavior:** Batch fetch prices in one call via `market_data_cache` or bulk yfinance/Finnhub query. If a price cannot be fetched, fall back to last recorded trade price rather than defaulting to `0.0`.
- **Severity:** P1 (Financial Display Distortion / High Latency)
- **Status:** CONFIRMED BUG

---

### Defect 3: Silent Provider Failures Masked as HTTP 200 Empty Arrays
- **File / Location:** [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L776-L779), [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L818-L823)
- **Code:**
  ```python
  except Exception as e:
      app.logger.warning(f"Sentiment live processing error for {ticker}: {e}")
      return jsonify({"status": "success", "data": []}), 200
  ```
- **Reproduction Conditions:** External upstream provider fails (e.g. rate limit 429, timeout, network error).
- **Actual Behavior:** The route catches the exception, logs a warning, and returns HTTP 200 with an empty list `[]`. The client receives `{"status": "success", "data": []}` and cannot determine whether the asset genuinely has no news or if the backend encountered a failure.
- **Expected Behavior:** Return appropriate status code or an explicit metadata payload (e.g. `{"status": "partial", "error": "Provider unavailable", "data": []}`) with client distinction.
- **Severity:** P2 (Integration & Observability)
- **Status:** CONFIRMED BUG

---

### Defect 4: Database Auto-Initialization at Module Import Time
- **File / Location:** [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L22)
- **Code:**
  ```python
  import database
  database.init_db()
  ```
- **Reproduction Conditions:** Importing `app.py` in test files or external tools.
- **Actual Behavior:** Executing `import app` automatically runs `database.init_db()` against `Config.DB_PATH` before test configuration can redirect to an in-memory or temporary database.
- **Expected Behavior:** Database initialization should occur in an explicit app factory or `create_app()` startup lifecycle hook.
- **Severity:** P2 (Architecture / Testing Isolation)
- **Status:** CONFIRMED BUG

---

## 3. Architecture Strengths Verified

1. **Process Locking:** [src/worker_manager.py](file:///c:/Users/Atul/project/stock-main/src/worker_manager.py) successfully prevents duplicate background worker threads across multi-process deployments.
2. **Atomic Trading Transactions:** [src/database.py](file:///c:/Users/Atul/project/stock-main/src/database.py#L1711) enforces `BEGIN IMMEDIATE` and rollback handling in `execute_trade_atomic()`.
3. **Dual Liveness & Readiness Probes:** Operational at `/api/health`, `/api/health/live`, and `/api/health/ready`.
4. **Structured Error Handling:** [src/error_handler.py](file:///c:/Users/Atul/project/stock-main/src/error_handler.py) formats 400, 401, 403, 404, 429, and 500 into predictable JSON envelopes.
