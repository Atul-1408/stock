# AUDIT 07: Authentication and Application Security Audit

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Audit Date:** 2026-10-28  
**Auditor:** Application Security Auditor (AppSec & Pen-Testing)  
**Status:** AUDIT ONLY (Read-Only Inspection)

---

## 1. Security Architecture Assessment

| Domain | Mechanism | Audit Status | Findings |
| :--- | :--- | :--- | :--- |
| **Password Storage** | Werkzeug `generate_password_hash` (scrypt) | **SECURE** | Industry standard, strong cost factors |
| **Authentication** | Flask-JWT-Extended Bearer tokens | **SECURE** | 32-byte production requirement enforced |
| **Timing Attacks** | Dummy hash execution on invalid/missing users | **SECURE** | [src/app.py:L427](file:///c:/Users/Atul/project/stock-main/src/app.py#L427) mitigates timing discrepancies |
| **SQL Injection** | Parameterized queries with SQLite placeholders (`?`) | **SECURE** | 0 dynamic SQL concatenations detected |
| **Rate Limiting** | Flask-Limiter (memory storage / Redis configurable) | **SECURE** | Enforced on login (5/min), OTP (5/min), trades (30/min) |
| **CORS Policy** | Origin whitelisting without wildcard in production | **SECURE** | Wildcard `*` prohibited in production |
| **Security Headers** | Nosniff, Frame-Options, HSTS, COOP, Referrer-Policy | **SECURE** | Injected on every response via `after_request` |
| **Trading Safety** | Dual-authorization switch (`TRADING_MODE` + `ALLOW_LIVE_TRADING`) | **SECURE** | Paper trading hard-enforced by default |

---

## 2. Security Vulnerabilities & Operational Risks

### Finding 1: Test Suite Modifies Active Production Database (Data Contamination Risk)
- **File / Location:** [tests/test_phase1_security.py](file:///c:/Users/Atul/project/stock-main/tests/test_phase1_security.py#L44-L60) & [tests/test_phase4_integration.py](file:///c:/Users/Atul/project/stock-main/tests/test_phase4_integration.py#L41)
- **Code:**
  ```python
  from src.app import app
  import src.database as database

  database.init_db()
  cls.user1_id = database.create_user(...)
  ```
- **Vulnerability:** The test suite does not redirect `Config.DB_PATH` to an in-memory SQLite database (`:memory:`) or an isolated temporary directory. Running `pytest` creates real test users (e.g. `sec_test_user1@example.com`), mutates account balances, and writes dummy trades directly to the user's active database file [data/stock_dashboard.db](file:///c:/Users/Atul/project/stock-main/data/stock_dashboard.db).
- **Impact:** Production database pollution, accidental overwriting of administrative accounts, and loss of production data integrity during routine CI/CD test execution.
- **Recommended Remediation:** In test setup, configure `Config.DB_PATH = Path(tempfile.mkdtemp()) / "test.db"` or `sqlite3.connect(":memory:")`.
- **Severity:** P1 (Data Contamination / Operational Security)
- **Status:** CONFIRMED BUG

---

### Finding 2: Transient In-Memory JWT Secret in Development
- **File / Location:** [src/config.py](file:///c:/Users/Atul/project/stock-main/src/config.py#L34-L35)
- **Code:**
  ```python
  else:
      import secrets
      JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
  ```
- **Vulnerability:** If `JWT_SECRET_KEY` is not explicitly declared in `.env`, a fresh random hex key is generated in memory upon every process startup.
- **Impact:** Every time the backend auto-reloads during development or code inspection, all existing JWT tokens in developer browsers are immediately invalidated, forcing unexpected session logouts.
- **Severity:** P3 (Developer Ergonomics & Session Stability)
- **Status:** CONFIRMED BEHAVIOR

---

### Finding 3: OTP Code Fallback Exposure in Console Logs
- **File / Location:** [src/otp_service.py](file:///c:/Users/Atul/project/stock-main/src/otp_service.py#L27-L29)
- **Actual Behavior:** When Gmail SMTP credentials are not configured, OTP generation still succeeds and outputs the verification code directly to the backend terminal log.
- **Security Assessment:** In local development, this is a helpful fallback. However, in shared or multi-tenant staging environments, printing one-time authentication codes to standard output poses a credential leakage risk if logs are aggregated to centralized third-party logging platforms.
- **Severity:** P2 (Information Disclosure in Staging/Prod)
- **Status:** VERIFIED BEHAVIOR (Intentional Dev Ergonomic / Prod Risk)

---

## 3. Summary of Phase 7 Findings

| ID | Finding | Severity | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Test suites execute directly against persistent active database | High | P1 | CONFIRMED BUG |
| **SEC-02** | OTP verification codes printed to standard output on unconfigured SMTP | Medium | P2 | VERIFIED BEHAVIOR |
| **SEC-03** | Auto-generated transient JWT secret on unconfigured development restarts | Low | P3 | VERIFIED BEHAVIOR |
| **SEC-04** | Dual authorization safety lock prevents accidental live trading | Info | — | VERIFIED WORKING |
| **SEC-05** | SQL injection protection verified via complete parameterization | Info | — | VERIFIED WORKING |
