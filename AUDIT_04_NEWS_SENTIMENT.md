# AUDIT 04: News and Sentiment Pipeline Audit

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Audit Date:** 2026-10-28  
**Auditor:** Senior Financial Systems QA Engineer & Machine Learning Specialist  
**Status:** AUDIT ONLY (Read-Only Inspection)

---

## 1. Pipeline Architecture Traced

```text
External News Source (yfinance -> NewsAPI -> Finnhub)
      │
      ▼
Normalization ([src/news_service.py](file:///c:/Users/Atul/project/stock-main/src/news_service.py))
  - URL Canonicalization (stripping UTM, ref, gclid, fbclid)
  - Title Normalization (stripping HTML, normalizing whitespace)
  - UTC ISO-8601 Timestamp Parsing
      │
      ▼
Deduplication (`canonicalize_url` + `compute_article_hash`)
      │
      ▼
Sentiment Scoring ([src/sentiment_service.py](file:///c:/Users/Atul/project/stock-main/src/sentiment_service.py))
  - FinBERT / VADER calibrated confidence
  - Signed sentiment mapping (-1.0 to +1.0)
      │
      ▼
Database Caching (`articles` & `sentiments` tables)
      │
      ▼
API Endpoints (`/api/news/<ticker>`, `/api/sentiment/<ticker>`, `/api/market/brief`)
      │
      ▼
UI Visualization ([NewsFeed.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/NewsFeed.jsx), [SentimentChart.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/SentimentChart.jsx), [MarketMood.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/MarketMood.jsx))
```

---

## 2. Findings and Pipeline Defects

### Defect 1: General Market News Mislabeled as Specific Company News in Finnhub Fallback
- **File / Location:** [src/news_service.py](file:///c:/Users/Atul/project/stock-main/src/news_service.py#L180-L203)
- **Code:**
  ```python
  # 3. Tertiary: Finnhub news fallback if key available
  if not articles:
      finnhub_key = os.getenv("FINNHUB_API_KEY", "").strip()
      if finnhub_key:
          category = "crypto" if ticker_clean.endswith("-USD") or "BTC" in ticker_clean else "general"
          resp = requests.get(
              "https://finnhub.io/api/v1/news",
              params={"category": category, "token": finnhub_key},
              timeout=8,
          )
          if resp.status_code == 200:
              for it in (resp.json() or [])[:limit]:
                  articles.append({
                      "ticker": ticker_clean,
                      "title": it.get("headline", ""),
                      "url": it.get("url", ""),
                      "source": it.get("source") or "Finnhub",
                      ...
                  })
  ```
- **Reproduction Conditions:** A ticker with no articles on yfinance or NewsAPI falls back to Finnhub.
- **Actual Behavior:** Calls `https://finnhub.io/api/v1/news?category=general`, which returns macroeconomic and general market news. The function then stamps each item with `"ticker": ticker_clean`. For example, macro news about the Federal Reserve or commodities is saved into the database and presented to the user as specific news for `TCS.NS` or `RELIANCE.NS`.
- **Expected Behavior:** Company news on Finnhub must use `https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start}&to={end}`. The general news endpoint should only be used for macro briefings or when category is explicitly general.
- **Severity:** P1 (Data Integrity / Incorrect Financial Attribution)
- **Status:** CONFIRMED BUG

---

### Defect 2: On-Demand News Ingestion Without Pre-fetching
- **File / Location:** [src/news_service.py](file:///c:/Users/Atul/project/stock-main/src/news_service.py#L208) & [src/worker_manager.py](file:///c:/Users/Atul/project/stock-main/src/worker_manager.py)
- **Actual Behavior:** News is fetched exclusively on-demand when a user navigates to `/api/news/<ticker>`. There is no background worker scheduled to periodically ingest and score news for the core stock universe.
- **User Impact:** First page load for any stock requires synchronous upstream network round-trips to yfinance/NewsAPI plus local sentiment scoring, causing a 2-4 second delay on cold tickers.
- **Severity:** P2 (Latency & User Experience)
- **Status:** PARTIALLY IMPLEMENTED (Works on-demand, lacks automated background ingestion worker)

---

### Defect 3: Deduplication Performance Edge-Case
- **File / Location:** [src/news_service.py](file:///c:/Users/Atul/project/stock-main/src/news_service.py#L101-L130)
- **Evidence:** Pytest benchmark failure:
  `tests/test_phase6_qa_performance.py::TestPhase6QAPerformance::test_10_deduplication_performance FAILED`
  `AssertionError: 53.22ms not less than 50.0ms : Deduplication took 53.22ms, expected < 50ms`
- **Root Cause:** In Python 3.14 on Windows, regex substitutions in `canonicalize_url` across 1,000 articles took 53ms.
- **Severity:** P3 (Minor Performance Threshold)
- **Status:** CONFIRMED BUG (Test assertion threshold violation)

---

## 3. Summary of Phase 4 Findings

| ID | Finding | Severity | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| **NEWS-01** | Finnhub fallback uses `/v1/news` instead of `/v1/company-news`, misattributing macro news to individual tickers | High | P1 | CONFIRMED BUG |
| **NEWS-02** | Absence of automated background news ingestion worker (relies purely on user-triggered requests) | Medium | P2 | PARTIALLY IMPLEMENTED |
| **NEWS-03** | 1,000-article deduplication benchmark exceeded 50ms target (53.22ms) in test suite | Low | P3 | CONFIRMED BUG |
| **NEWS-04** | Dual FinBERT / VADER sentiment fallback operates reliably with calibrated confidence | Info | — | VERIFIED WORKING |
