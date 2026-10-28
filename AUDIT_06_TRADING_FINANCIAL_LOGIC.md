# AUDIT 06: Financial Logic and Paper Trading Audit

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Audit Date:** 2026-10-28  
**Auditor:** Senior Financial Systems QA Engineer & Quantitative Systems Architect  
**Status:** AUDIT ONLY (Read-Only Inspection)

---

## 1. Paper Trading Account Initialization

- **$100,000 Paper Balance Verification:**
  - Database table: `users`
  - Columns: `starting_balance REAL DEFAULT 100000.00`, `current_balance REAL DEFAULT 100000.00`
  - Implementation: When a user registers via [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L406) (`database.create_user`), SQLite assigns the default $100,000.00 balance.
  - **Verdict:** VERIFIED WORKING. The $100k balance is an actual persisted database account balance, not a hardcoded frontend mock.

---

## 2. Order Execution & Financial Calculations

### Market Orders (Atomic Execution)
- Handled by `execute_trade_atomic()` in [src/database.py](file:///c:/Users/Atul/project/stock-main/src/database.py#L1711).
- **Concurrency & Atomicity:** Employs `BEGIN IMMEDIATE` transaction locking to guarantee atomic balance deduction, portfolio position updating, order creation, and transaction logging.
- **Validation:**
  - Rejects $NaN$, $\pm\infty$, zero, and negative quantities.
  - Rejects BUY orders when `current_balance < total_value`.
  - Rejects SELL orders when `existing_shares < quantity` (prevents naked overselling).
- **Position Averaging:**
  - On BUY: Calculates accurate weighted average entry price:
    $$\text{new\_avg\_price} = \frac{\text{existing\_total\_invested} + (quantity \times price)}{\text{existing\_shares} + quantity}$$
  - On SELL: Proportional investment reduction:
    $$\text{new\_total\_invested} = \max(0.0, \text{existing\_total\_invested} - (quantity \times \text{avg\_buy\_price}))$$
    Position is deleted if remaining shares $\le 0.000001$.

---

## 3. High-Priority Financial Logic Defects

### Defect 1: Un-escrowed Cash on Limit Orders (Double-Spending Exposure)
- **File / Location:** [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L1451-L1473)
- **Code:**
  ```python
  # Handle pending non-market orders (LIMIT / SL / SL-M)
  user_balance = database.get_user_balance(user_id) or 0.0
  if side == 'BUY':
      total_required = qty * validation_price
      if user_balance < total_required:
          return error_response(...)

  order_id = database.create_order(...)
  return jsonify({"status": "success", "order_id": order_id}), 201
  ```
- **Actual Behavior:** When a user places a pending LIMIT BUY order, the route checks if `user_balance >= total_required`, but **does not reserve or escrow** the required cash from `user.current_balance`.
- **Financial Consequence:** A user with $10,000 cash can submit five simultaneous $10,000 LIMIT BUY orders. Each order check passes because balance remains $10,000. If multiple orders were filled, the account balance would drop into negative territory.
- **Expected Behavior:** Place funds into an `escrow_balance` or deduct immediately from `current_balance` upon placing any LIMIT BUY order, releasing back if the order is cancelled.
- **Severity:** P1 (Financial Calculation & Risk Defect)
- **Status:** CONFIRMED BUG

---

### Defect 2: Missing Limit Order Matching Engine (Pending Orders Never Fill)
- **File / Location:** [src/app.py](file:///c:/Users/Atul/project/stock-main/src/app.py#L1466-L1471) & [src/worker_manager.py](file:///c:/Users/Atul/project/stock-main/src/worker_manager.py)
- **Actual Behavior:** Non-market orders (`LIMIT`, `SL`, `SL-M`) are inserted into the `orders` table with `status = 'OPEN'`. However, there is **zero background worker, scheduler, or price trigger engine** in the entire application that inspects open orders against market prices.
- **Consequence:** Open LIMIT and STOP-LOSS orders remain in `status = 'OPEN'` indefinitely and are never filled, regardless of how market prices fluctuate.
- **Expected Behavior:** An order matching worker should evaluate active open orders whenever new market prices are received by `MarketDataFeed`.
- **Severity:** P1 (Core Trading Feature Incomplete)
- **Status:** NOT IMPLEMENTED

---

### Defect 3: Autonomous Trading Bot Completely Disconnected from User Portfolio
- **File / Location:** [src/trading_bot/bot_engine.py](file:///c:/Users/Atul/project/stock-main/src/trading_bot/bot_engine.py#L351-L396)
- **Code:**
  ```python
  def _execute_bot_trade(self, user_id: int, signal: Dict, config: Dict) -> None:
      ...
      cursor.execute("""
          INSERT INTO bot_trades
          (user_id, ticker, action, shares, entry_price, stop_loss, take_profit, ...)
          VALUES (?, ?, ?, ?, ?, ?, ?, ...)
      """)
  ```
- **Actual Behavior:** When the autonomous bot engine executes a trade, it only writes a row to the `bot_trades` table. It **does not check available account cash**, **does not deduct money from `users.current_balance`**, and **does not update `portfolio`**.
- **Financial Consequence:** Bot trading runs in an isolated vanity sandbox. Bot profits or losses never reflect in the user's paper balance or institutional portfolio dashboard.
- **Expected Behavior:** Bot trades should invoke `execute_trade_atomic()` or a dedicated bot ledger account with strict risk-allocated capital limits.
- **Severity:** P1 (Architectural Disconnection & Misleading Ledger)
- **Status:** CONFIRMED BUG

---

### Defect 4: Missing Realized P&L in Transaction Audit Ledger
- **File / Location:** [src/database.py](file:///c:/Users/Atul/project/stock-main/src/database.py#L1820-L1826)
- **Actual Behavior:** The `transactions` table records `user_id, ticker, action, shares, price_per_share, total_value, timestamp`, but has no `realized_pnl` column. When a position is closed, the realized profit or loss is not logged in the transaction ledger.
- **Expected Behavior:** Record `realized_pnl` on every SELL transaction for instant portfolio accounting and tax/performance reporting.
- **Severity:** P2 (Accounting & Analytics Discrepancy)
- **Status:** CONFIRMED BUG

---

## 4. Summary of Phase 6 Findings

| ID | Finding | Severity | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FIN-01** | Limit order cash reservation not implemented (allows multi-order overspending) | High | P1 | CONFIRMED BUG |
| **FIN-02** | Limit/Stop-Loss order matching worker absent (pending orders never execute) | High | P1 | NOT IMPLEMENTED |
| **FIN-03** | Autonomous bot trades disconnected from user balance and portfolio | High | P1 | CONFIRMED BUG |
| **FIN-04** | Realized P&L not stored in `transactions` audit log | Medium | P2 | CONFIRMED BUG |
| **FIN-05** | $100,000 starting balance persisted in database schema and initialized on signup | Info | — | VERIFIED WORKING |
| **FIN-06** | Atomic market order execution with rollback protection | Info | — | VERIFIED WORKING |
