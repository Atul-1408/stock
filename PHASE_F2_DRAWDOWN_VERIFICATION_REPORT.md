# PHASE F.2 — MAXIMUM DRAWDOWN METHODOLOGY VERIFICATION REPORT

**Status:** STRICTLY READ-ONLY AUDIT  
**Scope:** Maximum Drawdown Methodology and Historical Equity Reconstruction  
**Date:** 2026-10-31  
**Trading Mode:** `PAPER` (`ALLOW_LIVE_TRADING=false`)  

---

## 1. Executive Summary

This independent audit evaluated the methodology, data pipeline, and formulas governing the maximum drawdown metric in `src/analytics_engine.py` and its presentation in `frontend/src/pages/AnalyticsDashboard.jsx`.

The audit confirmed that **maximum drawdown is currently UNRELIABLE and NOT TRUSTWORTHY** for production or historical performance reporting. The database lacks persistent end-of-day equity balance snapshots, the on-the-fly reconstruction contaminates historical valuations with current live prices when Yahoo Finance requests fail, a timestamp string comparison defect excludes same-day transactions, and empty or 1-day histories return `0.0` which the frontend displays as `"-0.0%"` rather than `"N/A"`.

| Checkpoint | Scope | Verdict | Primary Finding |
|---|---|---|---|
| **1. Data Reconstruction** | `calculate_max_drawdown` & `get_portfolio_history` | **FAIL** | No database snapshot table exists; on-the-fly reconstruction has multiple data integrity gaps. |
| **2. Historical Price Integrity** | `get_historical_price` fallback behavior | **FAIL** | Falls back to current live price (`trading_engine.get_current_price`) when historical price is $\le 0$. |
| **3. Cash & Flow Consistency** | Transactions, deposits, withdrawals, cash | **FAIL** | Cash reconstruction uses current `starting_balance`; timestamp string comparison excludes same-day transactions. |
| **4. Peak-to-Trough Formula** | Drawdown formula & series order | **PASS WITH ISSUES** | Series is chronological; formula is standard but lacks guards for non-positive peak equity. |
| **5. Availability Reporting** | Reporting `None`/N/A vs misleading values | **FAIL** | Insufficient data (`len(values) < 2`) returns `0.0` instead of `None`/`null`. |
| **6. False Drawdown Protection** | Missing prices & unpriced holdings | **FAIL** | Missing historical prices drop holding value or substitute live prices, creating artificial drawdowns. |
| **7. Frontend Presentation** | Display of `"N/A"` on unavailable metrics | **FAIL** | Frontend checks `!= null`, so backend `0.0` renders as `"-0.0%"` rather than `"N/A"`. |
| **8. Trading Safety & DB Protection** | Paper trading & database state | **PASS** | `TRADING_MODE=PAPER`, `ALLOW_LIVE_TRADING=False`, active database rows unchanged. |

**OVERALL VERDICT:** **FAIL (METHODOLOGY NOT TRUSTWORTHY)**

---

## 2. Exact Code Paths Reviewed

1. **Top-Level Analytics Entry Point:**
   - [src/analytics_engine.py](file:///c:/Users/Atul/project/stock-main/src/analytics_engine.py#L174-L178):
     ```python
     max_drawdown = 0.0
     try:
         max_drawdown = float(calculate_max_drawdown(user_id))
     except Exception:
         pass
     ...
     'max_drawdown': round(max_drawdown * 100, 2) if max_drawdown else 0.0
     ```
2. **Drawdown Calculation:**
   - [src/analytics_engine.py](file:///c:/Users/Atul/project/stock-main/src/analytics_engine.py#L297-L308):
     ```python
     def calculate_max_drawdown(user_id):
         """Max peak-to-trough decline."""
         history = get_portfolio_history(user_id)
         values = history['values']
         if len(values) < 2: return 0
         peak = values[0]
         max_dd = 0
         for v in values:
             if v > peak: peak = v
             dd = (peak - v) / peak
             if dd > max_dd: max_dd = dd
         return max_dd
     ```
3. **Daily History Generation:**
   - [src/analytics_engine.py](file:///c:/Users/Atul/project/stock-main/src/analytics_engine.py#L218-L237):
     Generates daily calendar series from first transaction date to `datetime.now().date()`, calling `calculate_portfolio_value_on_date(user_id, current_date)`.
4. **Historical Valuation Reconstruction:**
   - [src/analytics_engine.py](file:///c:/Users/Atul/project/stock-main/src/analytics_engine.py#L253-L277):
     Reconstructs cash and inventory per date, fetching prices via `get_historical_price(ticker, date)`.
5. **Historical Price Fetcher & Fallback:**
   - [src/analytics_engine.py](file:///c:/Users/Atul/project/stock-main/src/analytics_engine.py#L8-L21) & lines 272–275:
     ```python
     price = get_historical_price(ticker, date)
     if price <= 0:
         price = trading_engine.get_current_price(ticker)
     ```
6. **Transaction Fetching Query:**
   - [src/database.py](file:///c:/Users/Atul/project/stock-main/src/database.py#L1067-L1077):
     ```python
     def get_transactions_before_date(user_id: int, date: datetime) -> List[Dict]:
         target_date = date.strftime('%Y-%m-%d %H:%M:%S')
         ...
         cursor.execute(
             "SELECT * FROM transactions WHERE user_id = ? AND timestamp <= ? ORDER BY timestamp ASC",
             (user_id, target_date)
         )
     ```
7. **Frontend Display:**
   - [frontend/src/pages/AnalyticsDashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/AnalyticsDashboard.jsx#L441-L448):
     ```jsx
     <div className="text-sm font-bold text-coral-400 mt-0.5">
       {risk?.max_drawdown != null
         ? `-${Number(risk.max_drawdown).toFixed(1)}%`
         : analytics?.max_drawdown != null
         ? `-${Number(analytics.max_drawdown).toFixed(1)}%`
         : "N/A"}
     </div>
     ```

---

## 3. Detailed Findings by Checkpoint

### Checkpoint 1: Data Used to Reconstruct Historical Portfolio Equity
- **Finding:** **FAIL**
- **Analysis:**
  - The SQLite database contains no table for daily balance or equity snapshots (`daily_equity_snapshots` or `balance_history`).
  - Equity history is dynamically reconstructed by querying all `transactions` up to each day and querying external Yahoo Finance daily closes.
  - If a user has made no transactions, `get_portfolio_history` returns `dates: [], values: []`.
  - Because no authoritative ledger snapshots are persisted at the end of each trading day, the reconstructed series is brittle and depends entirely on runtime API availability.

### Checkpoint 2: Historical vs. Current Market Prices
- **Finding:** **FAIL**
- **Analysis:**
  - `get_historical_price(ticker, date)` calls `yf.Ticker(ticker).history(start, end)`. When offline, rate-limited, outside market hours, or for unlisted assets, `df.empty` causes it to return `0.0`.
  - In `calculate_portfolio_value_on_date`:
    ```python
    if price <= 0:
        price = trading_engine.get_current_price(ticker)
    ```
  - This directly substitutes **today's latest live price** into historical valuation dates from weeks or months ago.
  - Treating current market prices as historical market prices violates financial accounting standards and invalidates historical equity series.

### Checkpoint 3: Cash Balances, Timestamps, and Flow Consistency
- **Finding:** **FAIL**
- **Analysis:**
  - **Timestamp Comparison Flaw:** Transactions store UTC ISO strings (e.g. `'2026-10-31T15:30:00+00:00'`). In `database.get_transactions_before_date()`, `target_date = date.strftime('%Y-%m-%d %H:%M:%S')` produces `'2026-10-31 00:00:00'`. In ASCII string comparison, `'T' > ' '`, meaning `'2026-10-31T...' <= '2026-10-31 00:00:00'` evaluates to `False`. All transactions executed on that date are dropped from that date's valuation.
  - **Cash Balance Flaw:** `cash = database.get_starting_balance(user_id)`. If the user deposited funds or if `starting_balance` changed, all historical dates prior to that deposit assume the new starting balance. There is no deposit/withdrawal ledger.
  - **Dust Holdings:** `if holdings[ticker] <= 0: del holdings[ticker]`. Floating point inaccuracies (e.g., `10.0 - 9.999999 = 0.000001`) leave fractional ghost shares that continue being priced indefinitely.

### Checkpoint 4: Peak-to-Trough Drawdown Formula & Ordering
- **Finding:** **PASS WITH ISSUES**
- **Analysis:**
  - The day-by-day iteration in `get_portfolio_history` generates a strictly chronological equity series.
  - The formula `dd = (peak - v) / peak` is standard.
  - **Issue:** If `peak <= 0` (e.g., negative equity or zero cash starting point), the loop will throw a `ZeroDivisionError` or yield mathematically invalid negative percentages. There is no `if peak > 0:` guard.

### Checkpoint 5: Availability Reporting (`None` vs Misleading Values)
- **Finding:** **FAIL**
- **Analysis:**
  - If `len(values) < 2` (empty portfolio, brand new user, or 1-day trade history), `calculate_max_drawdown` returns `0`.
  - `calculate_portfolio_performance` formats this as `'max_drawdown': 0.0`.
  - Returning `0.0` misleads users into believing that the portfolio experienced zero drawdown over time, when in reality there was insufficient data to evaluate drawdown. It must return `None`.

### Checkpoint 6: False Drawdown Artifacts from Missing Prices
- **Finding:** **FAIL**
- **Analysis:**
  - If a user holds 100 shares of XYZ bought at $100 ($10,000 cost basis), cash drops from $10,000 to $0.
  - If on a subsequent date `get_historical_price` and `get_current_price` both fail to return a positive price, `shares * price` is not added to `p_value`.
  - `p_value` evaluates to $0.00 (cash only).
  - The equity curve records a drop from $10,000 to $0.00, reporting a fabricated **100% maximum drawdown** purely due to a failed price API call.

### Checkpoint 7: Frontend Presentation & N/A Handling
- **Finding:** **FAIL**
- **Analysis:**
  - In `frontend/src/pages/AnalyticsDashboard.jsx` (line 445):
    ```jsx
    analytics?.max_drawdown != null ? `-${Number(analytics.max_drawdown).toFixed(1)}%` : "N/A"
    ```
  - Because the backend returns `0.0` instead of `null`, `analytics?.max_drawdown != null` evaluates to `true`.
  - The UI renders `"-0.0%"` instead of `"N/A"`.
  - Note: `risk?.max_drawdown` is always `undefined` because `/api/analytics/risk` only returns `beta`, `alpha`, `r_squared`, and `sortino_ratio`.

### Checkpoint 8: Trading Safety & Database Protection
- **Finding:** **PASS**
- **Analysis:**
  - Runtime verified: `TRADING_MODE: PAPER`, `ALLOW_LIVE_TRADING: False`, `IS_LIVE_TRADING_ENABLED: False`.
  - Zero live brokerage endpoints exist.
  - Active user database row counts verified unchanged (`orders`: 27, `transactions`: 19, `portfolio`: 2, `users`: 10).
  - Note: Connecting to SQLite without `?mode=ro` increments the internal 4-byte database file change counter on close even for SELECT statements; future verification tooling must use `file:... ?mode=ro` with URI connections to preserve file hashes.

---

## 4. Trustworthiness Assessment

### **Is Maximum Drawdown Trustworthy for the Current Application?**
### **NO.**

The maximum drawdown metric in its current implementation cannot be trusted for financial decision-making or production dashboards. The metric suffers from:
1. Artificial drawdowns caused by transient price fetch failures.
2. Contamination of historical valuations with contemporary prices.
3. Timestamp format mismatches dropping intraday transactions.
4. Masking insufficient data as `0.0%` drawdown instead of `"N/A"`.

---

## 5. Recommended Remediation Plan (For Future Implementation)

When authorized to remediate in a future phase, apply the following minimal, targeted fixes:

1. **Mark Unavailable When Insufficient Data:**
   - In `src/analytics_engine.py`:
     - Update `calculate_max_drawdown(user_id)` to return `None` when `len(values) < 2`.
     - In `calculate_portfolio_performance(user_id)`, set `'max_drawdown': round(max_drawdown * 100, 2) if max_drawdown is not None else None`.
2. **Never Substitute Current Price for Historical Price:**
   - In `calculate_portfolio_value_on_date(user_id, date)`:
     - If `get_historical_price(ticker, date) <= 0`, do NOT fall back to `trading_engine.get_current_price(ticker)`.
     - If any holding cannot be priced on a historical date, mark that date's equity as unavailable (`None`) or skip that date from the drawdown calculation rather than dropping the asset value to zero.
3. **Fix Timestamp Filtering:**
   - In `src/database.py` (`get_transactions_before_date`):
     - Format target timestamp as `target_date = date.strftime('%Y-%m-%dT23:59:59.999999')` to include all transactions occurring on that calendar date.
4. **Guard Non-Positive Peak in Drawdown Loop:**
   - In `calculate_max_drawdown`:
     ```python
     if peak <= 0:
         continue
     ```
5. **Frontend Guard:**
   - In `frontend/src/pages/AnalyticsDashboard.jsx`:
     - Ensure drawdown renders `"N/A"` whenever `analytics?.max_drawdown == null`.
6. **Architectural Recommendation (Future Phase):**
   - Introduce a `portfolio_snapshots` table:
     ```sql
     CREATE TABLE IF NOT EXISTS portfolio_snapshots (
         user_id INTEGER,
         date TEXT,
         cash_balance REAL,
         holdings_market_value REAL,
         total_equity REAL,
         PRIMARY KEY (user_id, date)
     );
     ```
     Persisting EOD equity snapshots eliminates reliance on retrospective yfinance reconstruction and guarantees deterministic, auditable drawdowns.

---

## 6. Final Recommendation

Keep the maximum drawdown metric flagged as **UNAVAILABLE / EXPERIMENTAL** until the remediation above is approved and implemented.

Do not start Phase G or begin code modifications. Awaiting explicit user instructions.
