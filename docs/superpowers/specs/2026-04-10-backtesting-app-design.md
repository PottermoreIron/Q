# Backtesting Cross-Platform App — Design Spec

**Date:** 2026-04-10
**Status:** Approved

---

## Context

A trading strategy backtesting application for web browsers and mobile (iOS/Android). Serves two user types: retail/hobby traders (no-code visual builder) and quant/algo traders (Python code editor). Architecture is designed to support paper trading, live broker integration, strategy marketplace, and AI suggestions in future versions — but v1 focuses on backtesting only.

---

## Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| Platforms | Web (Next.js) + Mobile (Expo/React Native) | Best Python editor (Monaco) on web; native mobile UX |
| Monorepo | Turborepo | Shared packages: `@app/api`, `@app/logic`, `@app/ui` |
| Backend | FastAPI (Python) | Matches backtesting engines; async, fast |
| Backtest engines | VectorBT (crypto/quant) + Backtrader (stocks/forex/futures) | Routed by asset class |
| Compute | Hybrid: light runs inline, heavy runs via Celery workers | Balance responsiveness with scale |
| Auth | Optional — works without login; sign up unlocks cloud sync | Lower barrier for new users |
| UI style | Clean & modern, light theme | Accessible to retail traders |
| Data sources | CSV upload + Yahoo Finance/Binance/Alpha Vantage + Polygon.io/Alpaca | All of the above |
| Asset classes | Stocks, Crypto, Forex, Futures/Options | Full coverage |
| Strategy input | Visual no-code block builder → auto-generates Python; editable | Layered: retail → quant |
| Storage | PostgreSQL + Redis + S3-compatible (MinIO or AWS S3) | Standard for this scale |

---

## Architecture

### Monorepo Structure

```
apps/
  web/          # Next.js 14 (App Router)
  mobile/       # Expo SDK 51 (React Native)
  api/          # FastAPI backend
packages/
  @app/api      # Typed API client (openapi-fetch + Zod)
  @app/logic    # Strategy validation, formatters, shared types
  @app/ui       # Shared React Native components
```

### Backend Services (FastAPI)

1. **Auth Service** — optional JWT auth, Google OAuth, anonymous session support
2. **Data Ingestion Service** — CSV/JSON upload (S3), Yahoo Finance (`yfinance`), Binance (`ccxt`), Alpha Vantage, Polygon.io, Alpaca
3. **Strategy Service** — CRUD; sandboxed Python validation (`RestrictedPython`); visual block → Python compiler
4. **Backtesting Engine Router** — Celery task queue; routes to:
   - **VectorBT**: crypto pairs, quant multi-asset
   - **Backtrader**: stocks, forex, futures/options
5. **Results Service** — Sharpe, Sortino, max drawdown, CAGR, win rate; equity curve; CSV/PDF export

### Data Layer

- **PostgreSQL** — users, strategies, backtest run metadata, result summaries
- **Redis** — Celery broker/result backend, API cache, session tokens
- **S3 / MinIO** — uploaded data files, large result datasets, exported reports

---

## Core Screens

### 1. Dashboard
Recent backtest runs, key stats (best Sharpe, best CAGR), quick-start CTA. Fully functional without login (results stored locally).

### 2. Strategy Builder
Split view: no-code drag-and-drop indicator blocks on the left auto-generate Python on the right. Advanced users edit the Python directly. Tab to toggle modes. Indicators: EMA, SMA, RSI, MACD, Bollinger Bands, custom. Entry/exit rules, position sizing, stop-loss/take-profit blocks.

### 3. Data Configuration
Source picker (upload / free API / paid API), symbol search, date range, timeframe (1m to 1M), preview of available data. Auto-detects asset class to route to correct backtest engine.

### 4. Run Backtest
Progress indicator with log output. Light runs (small data) execute immediately; heavy runs are async with real-time polling. Cancel button. Mobile shows push notification on completion.

### 5. Results Explorer
Equity curve (Recharts on web, Victory Native on mobile), metrics table, trade log with entry/exit details, multi-run comparison overlay, export to CSV or PDF.

---

## Data Flow

```
User defines strategy
  → Strategy Service validates Python (sandboxed RestrictedPython)
  → Data Ingestion fetches / serves cached OHLCV data
  → Engine Router detects asset class → dispatches Celery task
      → VectorBT worker  (crypto / quant)
      → Backtrader worker (stocks / forex / futures)
  → Results stored: summaries in PostgreSQL, large datasets in S3
  → Frontend polls job status → renders Results Explorer
```

---

## Error Handling

| Error | Handling |
|---|---|
| Invalid Python strategy | Sandbox returns line-level errors shown inline in Monaco editor |
| Data fetch failure | Retry with exponential backoff; fallback to cache; user-visible error with retry |
| Long-running job timeout | Celery timeout (default 5 min, configurable); user notified; mobile push on completion |
| Auth-less user | Data in localStorage / AsyncStorage; prompt to sign up to sync to cloud |
| Engine crash | Worker restarts automatically; job marked failed with error message |

---

## Testing Strategy

| Layer | Tool | What |
|---|---|---|
| Unit | Vitest (frontend), pytest (backend) | Individual functions, services |
| Integration | FastAPI TestClient + Docker PostgreSQL | API routes against real DB |
| E2E | Playwright | Web critical paths: strategy → run → results |
| Backtest correctness | Golden-file tests | Known strategy + known data → known metrics |
| Mobile | Expo + Detox (future) | Core navigation flows |

---

## Future Extension Points (v1 stubs only)

- `BrokerAdapter` interface → Alpaca, IBKR for paper/live trading
- `StrategyMarketplace` service stub → publish/discover community strategies
- `AIAdvisor` service stub → LLM-powered strategy suggestions
- `NotificationService` → extensible for email/push/webhooks

---

## Implementation Phases

| Phase | Scope |
|---|---|
| 1 — Scaffold | Turborepo, Next.js, Expo, FastAPI, Docker Compose, CI |
| 2 — Auth & Data | Optional auth, CSV upload, yfinance, ccxt (Binance) |
| 3 — Strategy Builder | No-code blocks, block→Python compiler, Monaco editor |
| 4 — Backtest Engine | Celery workers, VectorBT + Backtrader integration |
| 5 — Results & Polish | Results Explorer, metrics, export, mobile push notifications |
| 6 — Paid Data & QA | Polygon.io, Alpha Vantage, Alpaca, E2E tests, App Store prep |

---

## Verification Checklist

- [ ] `docker compose up` → all services healthy
- [ ] Upload sample OHLCV CSV → data visible in Data Configuration
- [ ] Define EMA crossover in no-code builder → correct Python generated
- [ ] Run backtest on BTC/USDT daily → VectorBT engine used, metrics correct
- [ ] Run backtest on AAPL daily → Backtrader engine used, metrics correct
- [ ] Export results as CSV → file downloads correctly
- [ ] Open web app on mobile browser → responsive layout works
- [ ] Install Expo app → all 5 screens navigable
