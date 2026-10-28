# AUDIT 05: Frontend and UI Functionality Audit

**Project:** Sovereign Intelligence — AI Stock Market Intelligence Dashboard  
**Audit Date:** 2026-10-28  
**Auditor:** Senior React / Frontend Engineer  
**Status:** AUDIT ONLY (Read-Only Inspection)

---

## 1. Frontend Architecture & Page Audit

The frontend is built with React 19, Vite 7, Tailwind CSS, and Chart.js.
- **Routing:** React Router v7 ([frontend/src/App.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/App.jsx))
- **Layout:** [TerminalLayout.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/layout/TerminalLayout.jsx), [TopBar.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/layout/TopBar.jsx), [Sidebar.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/layout/Sidebar.jsx)
- **State & Context:** [CurrencyContext.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/contexts/CurrencyContext.jsx)
- **API Client:** [frontend/src/utils/api.js](file:///c:/Users/Atul/project/stock-main/frontend/src/utils/api.js) (Axios with Bearer token injection and 401 redirect)

### Page Implementation Matrix

| Page Component | Route | Implementation State | Notes |
| :--- | :--- | :--- | :--- |
| [Dashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/Dashboard.jsx) | `/dashboard` | **Fully Implemented** | Charts, intelligence card, paper execution, active holdings |
| [MarketWatch.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/MarketWatch.jsx) | `/market` | **Fully Implemented** | Scanner filters, orders/positions; starved by unseeded DB |
| [AnalyticsDashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/AnalyticsDashboard.jsx) | `/analytics` | **Fully Implemented** | Risk metrics, win-rate, sector allocation |
| [AlertsPage.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/AlertsPage.jsx) | `/alerts` | **Fully Implemented** | Rule builder, trigger history, toggle/delete handlers |
| [LeaderboardPage.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/LeaderboardPage.jsx) | `/leaderboard` | **Fully Implemented** | Trader rankings, P&L comparisons, profile view |
| [ChatbotPanel.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/ChatbotPanel.jsx) | `/chat` | **Fully Implemented** | Multi-conversation history, markdown message rendering |
| [BotDashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/bot/BotDashboard.jsx) | `/bot` | **Fully Implemented** | Watchlist, signals, trade history, risk config |
| [LoginPage.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/LoginPage.jsx) | `/login` | **Fully Implemented** | Password login, OTP flow, Google OAuth button |
| [SignupPage.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/SignupPage.jsx) | `/signup` | **Fully Implemented** | Registration with validation & automatic redirect |

---

## 2. Top Stock Ticker Special Investigation

- **Files Inspected:**
  - Component: [frontend/src/components/TickerTape.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/components/TickerTape.jsx)
  - Service: [frontend/src/services/TickerService.js](file:///c:/Users/Atul/project/stock-main/frontend/src/services/TickerService.js)
  - Styles: [frontend/src/index.css](file:///c:/Users/Atul/project/stock-main/frontend/src/index.css)
- **Verification Results:**
  1. **Scrollbar Removal:** `no-scrollbar` class applied (`scrollbar-width: none; &::-webkit-scrollbar { display: none; }`). No visible horizontal scrollbar rendered.
  2. **Seamless Looping:** 2-group duplicate marquee layout (`renderTickerGroup("primary", false)` and `renderTickerGroup("duplicate", true)` with `aria-hidden="true"`).
  3. **Animation Physics:** Continuous `@keyframes ticker-scroll` (`translate3d(0, 0, 0)` to `translate3d(-50%, 0, 0)`) over 45s linear loop.
  4. **Hover Pause:** `.ticker-tape-track:hover { animation-play-state: paused; }` functional.
  5. **Reduced Motion Accessibility:** `@media (prefers-reduced-motion: reduce)` slows animation to 90s without converting to broken horizontal scroll.
  6. **Data Refresh:** `TickerService.js` maintains component subscriptions, batches tickers in sizes of 10, and updates prices without resetting the animation position.

---

## 3. Frontend Bugs and Regressions

### Defect 1: Hardcoded Currency Symbols in Dashboard Summary Widgets
- **File / Location:** [frontend/src/pages/Dashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/Dashboard.jsx#L163), [frontend/src/pages/Dashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/Dashboard.jsx#L171), [frontend/src/pages/Dashboard.jsx](file:///c:/Users/Atul/project/stock-main/frontend/src/pages/Dashboard.jsx#L193)
- **Code:**
  ```jsx
  <div className="text-sm font-bold text-white">
    ${Number((user?.current_balance || 0) + (portfolio?.total_market_value || 0)).toLocaleString("en-US", { minimumFractionDigits: 2 })}
  </div>
  ...
  <span className="text-lg font-bold text-white">${latestPrice.toFixed(2)}</span>
  ```
- **Actual Behavior:** Even though the user changes the global currency selector to `INR` (₹) or `EUR` (€), the primary dashboard summary cards and active asset prices hardcode the dollar sign (`$`) and bypass `convertPrice()`. For Indian NSE assets like `RELIANCE.NS`, prices in ₹ are rendered with a leading `$`.
- **Expected Behavior:** Render dynamic currency symbols using `getCurrencySymbol(currency)` and convert values with `convertPrice()`.
- **Severity:** P2 (UI Data Inconsistency)
- **Status:** CONFIRMED BUG

---

### Defect 2: Missing Automated Test & Linting Tooling
- **File / Location:** [frontend/package.json](file:///c:/Users/Atul/project/stock-main/frontend/package.json#L6-L10)
- **Actual Behavior:** `package.json` contains only `"dev"`, `"build"`, and `"preview"`. No unit testing framework (Vitest/Jest) or linter (ESLint) is configured.
- **Expected Behavior:** Include standard frontend test and lint scripts (`npm run test`, `npm run lint`).
- **Severity:** P3 (Developer Workflow & QA)
- **Status:** NOT IMPLEMENTED

---

## 4. Production Build Verification

Executed `npm run build` in `frontend/`:
```text
> frontend@0.0.0 build
> vite build

vite v7.3.1 building client environment for production...
✓ 2249 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                          1.15 kB │ gzip:   0.55 kB
dist/assets/index-zwpDTd2j.css          56.14 kB │ gzip:  10.34 kB
dist/assets/vendor-icons-N5zSkVyi.js    15.68 kB │ gzip:   5.68 kB
dist/assets/vendor-react-DT-4Dl59.js    47.46 kB │ gzip:  16.76 kB
dist/assets/vendor-motion-nHpJ0Okt.js  123.01 kB │ gzip:  40.62 kB
dist/assets/vendor-charts-CS9oMMYG.js  174.59 kB │ gzip:  61.00 kB
dist/assets/index-vmmDweJ1.js          439.44 kB │ gzip: 124.66 kB
✓ built in 20.99s
```
**Result:** PASSED with 0 errors.

---

## 5. Summary of Phase 5 Findings

| ID | Finding | Severity | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| **UI-01** | Top stock ticker horizontal scrolling, looping, and hover | Info | — | VERIFIED WORKING |
| **UI-02** | Hardcoded `$` symbols in Dashboard summary cards bypass currency context | Medium | P2 | CONFIRMED BUG |
| **UI-03** | Missing frontend test scripts (`npm test`) and linter (`eslint`) | Low | P3 | NOT IMPLEMENTED |
| **UI-04** | Production Vite build compiles cleanly with zero errors | Info | — | VERIFIED WORKING |
