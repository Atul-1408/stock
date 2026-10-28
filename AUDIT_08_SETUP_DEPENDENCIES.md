# AUDIT 08: Dependencies, Installation and Reproducibility Audit

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Audit Date:** 2026-10-28  
**Auditor:** Senior DevOps & Python Software Architect  
**Status:** AUDIT ONLY (Read-Only Inspection)

---

## 1. Dependency Manifest Inspection

| Component | Manifest File | Lockfile | Status | Findings |
| :--- | :--- | :--- | :--- | :--- |
| **Python Backend** | `requirements.txt` | *None* | **MISSING** | **Critical Defect:** No Python package manifest exists in the repository! |
| **Python Alternative** | `pyproject.toml` | *None* | **MISSING** | No pyproject or setup.py found. |
| **Node Frontend** | `frontend/package.json` | `package-lock.json` | **PRESENT** | React 19, Vite 7, Tailwind 3.4.17 installed & verified |

---

## 2. Key Reproducibility Issues Identified

### Defect 1: Total Absence of Python Dependency Manifest
- **File / Location:** Root repository directory & [README.md:L74](file:///c:/Users/Atul/project/stock-main/README.md#L74)
- **Documented Instruction:**
  ```bash
  pip install -r requirements.txt  # (if applicable, or install via pyproject.toml)
  ```
- **Actual Condition:** Neither `requirements.txt`, `pyproject.toml`, `Pipfile`, nor `setup.py` exists in the repository.
- **Evidence:** Fresh virtual environment `.venv/` contained only `pip 25.3` and immediately threw:
  ```text
  ModuleNotFoundError: No module named 'pandas'
  ```
- **Consequence:** Any new developer or automated CI/CD pipeline attempting to clone and run the repository cannot determine required packages or install them using standard tooling.
- **Required Packages Identified During Audit:**
  - `Flask>=3.1.0`
  - `flask-cors>=6.0.0`
  - `Flask-JWT-Extended>=4.7.0`
  - `Flask-Limiter>=3.8.0`
  - `requests>=2.31.0`
  - `python-dotenv>=1.0.0`
  - `pandas>=2.2.0`
  - `numpy>=1.26.0`
  - `yfinance>=0.2.40`
  - `vaderSentiment>=3.3.2`
  - `google-genai>=1.0.0`
  - `google-auth>=2.28.0`
  - `transformers>=4.40.0`
  - `pytest>=8.0.0`
  - `gunicorn>=22.0.0` (for Linux production) / `waitress` (Windows)
- **Severity:** P0 (Total Setup Failure for New Environments)
- **Status:** CONFIRMED BUG

---

### Defect 2: Windows Console `cp1252` Unicode Crash
- **File / Location:** [test_imports.py](file:///c:/Users/Atul/project/stock-main/test_imports.py#L15), [src/trading_bot/bot_engine.py](file:///c:/Users/Atul/project/stock-main/src/trading_bot/bot_engine.py#L26)
- **Error Observed:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u274c' in position 0: character maps to <undefined>
  ```
- **Root Cause:** Standard Windows PowerShell/CMD terminals default to legacy codepages (`cp1252`). When scripts print terminal status emojis (✅, ❌, 🤖, 🛑), Python raises an unhandled `UnicodeEncodeError`.
- **Mitigation:** Requires running with environment variable `PYTHONUTF8=1` or command line `python -X utf8`.
- **Severity:** P2 (Windows Developer Interruption)
- **Status:** CONFIRMED BUG

---

### Defect 3: Python 3.14 Compatibility Deprecation Warnings
- During execution under Python 3.14.2, multiple third-party libraries emitted forward-compatibility deprecation warnings:
  - `langsmith`: `UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.`
  - `google-genai`: `DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17`
  - `pytest-asyncio`: `DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16`
  - `vaderSentiment`: `DeprecationWarning: codecs.open() is deprecated. Use open() instead.`
- **Recommended Target:** Recommended standard runtime is Python 3.11 or 3.12 for long-term production stability.
- **Severity:** P3 (Future Compatibility)
- **Status:** CONFIRMED WARNING

---

## 3. Summary of Phase 8 Findings

| ID | Finding | Severity | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| **DEP-01** | Missing `requirements.txt` / `pyproject.toml` prevents clean installation | Critical | P0 | CONFIRMED BUG |
| **DEP-02** | Windows console `cp1252` encoding crashes on emoji print statements | Medium | P2 | CONFIRMED BUG |
| **DEP-03** | Python 3.14 emits upstream deprecation warnings (Python 3.11/3.12 recommended) | Low | P3 | CONFIRMED WARNING |
| **DEP-04** | Node.js frontend dependencies fully pinned and lockfile intact | Info | — | VERIFIED WORKING |
