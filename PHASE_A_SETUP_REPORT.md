# PHASE A SETUP AND DEPENDENCY REPAIR REPORT

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Date:** 2026-10-28  
**Phase:** Phase A — Setup & Dependencies Repair  
**Auditor/Engineer:** Senior Software Architect & DevOps Engineer  
**Status:** COMPLETE (Ready for Review)

---

## 1. Executive Summary

Phase A focused on repairing the repository's missing dependency manifests, establishing a reproducible installation workflow on Windows, and validating project imports and build pipelines without altering application trading logic or database schemas.

### Primary Accomplishments
1. **Created Root `requirements.txt`:** Fully inventoried all runtime, machine learning, and testing imports across `src/`, `scripts/`, `tests/`, and root files. Pinned compatible version ranges verified against the active Python runtime.
2. **Corrected `README.md` Installation Guide:** Replaced broken/placeholder instructions with accurate Windows PowerShell activation, dependency installation commands, and environment variable setup.
3. **Validated Safe Imports:** Executed an automated 31-module import validation check covering all core web, database, financial calculation, and AI libraries with a 100% pass rate.
4. **Verified Isolated Database Test Execution:** Confirmed how to redirect test runs away from the real database via `DATABASE_PATH` to prevent active database pollution.
5. **Verified Frontend Production Build:** Confirmed `npm run build` in `frontend/` compiles 2,249 modules with zero errors.

---

## 2. Dependency Inventory & Categorization

### A. Core Runtime Dependencies
- **`Flask>=3.0.0,<3.2.0`:** Primary REST API web framework.
- **`Flask-Cors>=5.0.0,<7.0.0`:** Cross-Origin Resource Sharing middleware.
- **`Flask-JWT-Extended>=4.6.0,<5.0.0`:** Stateless Bearer authentication & token management.
- **`Flask-Limiter>=3.5.0,<5.0.0`:** IP & route rate-limiting defense.
- **`Werkzeug>=3.0.0,<3.2.0`:** Secure password hashing (scrypt) and WSGI utilities.
- **`python-dotenv>=1.0.0`:** Environment variable loader for [.env](file:///c:/Users/Atul/project/stock-main/.env).
- **`requests>=2.31.0`:** Synchronous HTTP client for NewsAPI, Finnhub, and ExchangeRate-API.

### B. Financial Market Data & Analytical Engine
- **`pandas>=2.0.0`:** Time-series dataframes for price history and technical indicators.
- **`numpy>=1.24.0`:** High-performance vector calculations for risk metrics.
- **`yfinance>=0.2.35`:** Yahoo Finance market quote and historical OHLCV data ingest.
- **`pandas-ta-classic>=0.3.59`:** Technical analysis library (SMA, EMA, RSI, MACD).

### C. AI Financial Intelligence & Sentiment Analysis
- **`vaderSentiment>=3.3.2`:** Offline rule-based financial headline sentiment analysis.
- **`google-genai>=1.0.0`:** Google Gemini Flash Lite LLM SDK for Sovereign Neural Assistant.
- **`google-auth>=2.20.0`:** Google OAuth token verification and credentials transport.

### D. Autonomous Trading Bot & Machine Learning
- **`scikit-learn>=1.3.0`:** Random Forest & Gradient Boosting models (`models/*.pkl`).
- **`joblib>=1.3.0`:** Serialization/deserialization of trained ML model artifacts.
- **`schedule>=1.2.0`:** Cron-style periodic execution for background tasks.
- **`colorama>=0.4.6`:** Cross-platform terminal styling for bot logging.
- **`python-telegram-bot>=20.0`:** Real-time trade alert broadcast engine.
- **`matplotlib>=3.8.0` & `seaborn>=0.13.0`:** Offline strategy backtesting chart generators.

### E. Optional Deep Learning (FinBERT Transformer Pipeline)
- **`transformers>=4.40.0`:** HuggingFace transformer pipeline for FinBERT financial models.
- **`torch>=2.0.0`:** Deep learning tensor backend for transformer models.

### F. Quality Assurance & Testing
- **`pytest>=8.0.0`:** Unit and integration test runner.
- **`pytest-asyncio>=0.23.0`:** Asynchronous fixture support.

---

## 3. Verification & Test Execution Results

| Verification Test | Command | Outcome | Notes |
| :--- | :--- | :---: | :--- |
| **Dependency Resolution Check** | `python -m pip install --dry-run -r requirements.txt` | **100% SATISFIED** | All 25 required packages and transitive dependencies resolved with zero conflicts |
| **Comprehensive Import Validation** | `python -X utf8 scratch/test_all_imports.py` | **31 / 31 PASSED** | Tested Flask, JWT, pandas, numpy, yfinance, Gemini, scikit-learn, database, and worker manager |
| **Frontend Production Build** | `npm run build` in `frontend/` | **PASSED (20.99s)** | 2,249 modules transformed; generated `dist/` bundle cleanly |
| **Isolated Test Environment Probe** | `pytest tests/test_phase1_security.py` with isolated `DATABASE_PATH` | **18 PASSED / 1 FAILED** | Confirmed `test_13` fails on clean DB because `update_user_balance` was located in `else:` block of test setup |

---

## 4. List of Changed Files

1. [requirements.txt](file:///c:/Users/Atul/project/stock-main/requirements.txt) — **Created** (42 lines). Root dependency manifest with categorized and pinned dependencies.
2. [README.md](file:///c:/Users/Atul/project/stock-main/README.md) — **Updated** (lines 52–104). Clarified Windows PowerShell activation (`.\venv\Scripts\Activate.ps1`), requirements installation, and execution steps.
3. [PHASE_A_SETUP_REPORT.md](file:///c:/Users/Atul/project/stock-main/PHASE_A_SETUP_REPORT.md) — **Created**. This comprehensive setup and dependency audit report.

*(Zero application code files in `src/` or `frontend/src/` were modified.)*

---

## 5. Remaining Blockers Before Next Phases

1. **Test Suite Isolation Fixture (`SEC-01`):** In `tests/`, test suites should set a temporary SQLite database automatically via a `conftest.py` fixture so developers running `pytest` never accidentally overwrite `data/stock_dashboard.db`.
2. **Limit Order Cash Escrow (`FIN-01`) & Matching Worker (`FIN-02`):** Pending orders currently do not reserve cash and are never filled by a matching loop.
3. **Autonomous Bot Ledger Disconnection (`FIN-03`):** The trading bot operates exclusively inside `bot_trades` without debiting user paper balance.
4. **Market Scanner Cold Starvation (`MKT-01`):** `stock_universe` contains only 1 stock (AAPL) and needs an automatic startup migration to seed tracked stocks.
