# Q — Trading Strategy Backtesting

Cross-platform backtesting app for retail and quantitative traders. Build strategies visually or in Python, run them against historical data, and explore results.

**Web** (Next.js) · **Mobile** (Expo/React Native) · **Backend** (FastAPI + Python)

---

## What it does

- **Strategy Builder** — drag-and-drop no-code blocks that compile to Python; editable code in Monaco (web) or a read-only code viewer (mobile)
- **Backtesting Engine** — vectorised inline runner for short date ranges; Celery workers for heavy jobs; routes by asset class
- **Data Sources** — Yahoo Finance, Binance (ccxt), Polygon.io, Alpha Vantage, Alpaca, CSV upload
- **Results Explorer** — equity curve chart, 8-metric grid (Sharpe, Sortino, CAGR, max drawdown, win rate, profit factor, total trades, final value), trade log, CSV export
- **Multi-asset** — stocks, crypto, forex, futures, options

---

## Monorepo structure

```
apps/
  web/          Next.js 14 (App Router) — full web app
  mobile/       Expo SDK 51 (React Native) — iOS + Android
  api/          FastAPI backend
packages/
  logic/        Zod schemas + shared types (@app/logic)
```

---

## Quick start

### Prerequisites

- Node 20+, pnpm 10+
- Python 3.12, uv or pip
- Docker + Docker Compose

### 1. Infrastructure

```bash
docker compose up -d
```

Starts PostgreSQL 15, Redis 7, and the FastAPI container on ports 5432, 6379, 8000.

### 2. Environment

```bash
# Copy and fill in API keys (all optional — free sources work out of the box)
cp apps/api/.env.example apps/api/.env
```

Key variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Set automatically by Docker Compose |
| `REDIS_URL` | Yes | Set automatically by Docker Compose |
| `SECRET_KEY` | Yes | JWT signing key — set to any long random string |
| `POLYGON_API_KEY` | No | Polygon.io market data |
| `ALPHA_VANTAGE_API_KEY` | No | Alpha Vantage market data |
| `ALPACA_API_KEY` / `ALPACA_API_SECRET` | No | Alpaca market data |

### 3. Database migrations

```bash
cd apps/api
source .venv/bin/activate   # or: python -m venv .venv && pip install -r requirements.txt
alembic upgrade head
```

### 4. Install JS dependencies

```bash
pnpm install
```

### 5. Run

```bash
# All apps in parallel (Turborepo)
pnpm dev

# Or individually:
pnpm --filter @app/web dev        # → http://localhost:3000
pnpm --filter @app/mobile dev     # Expo dev server (scan QR with Expo Go)
```

---

## Testing

```bash
# All packages
pnpm test

# Backend only (requires Docker for PostgreSQL)
cd apps/api && pytest -v

# Web E2E (Playwright — starts Next.js dev server automatically)
pnpm --filter @app/web test:e2e
```

Backend test highlights:
- **Golden-file regression** — fixed synthetic data + known strategy must produce exact metrics
- **Connector unit tests** — Polygon, Alpha Vantage, Alpaca with mocked HTTP
- **API integration tests** — FastAPI TestClient against real PostgreSQL

---

## Stack

| Layer | Technology |
|---|---|
| Web | Next.js 14 · Tailwind CSS · Recharts · Vitest · Playwright |
| Mobile | Expo SDK 51 · expo-router |
| Shared types | `@app/logic` — Zod schemas |
| API | FastAPI 0.111 · SQLAlchemy 2 async · Alembic · Pydantic |
| Queue | Celery 5 · Redis 7 |
| Database | PostgreSQL 15 |
| Storage | MinIO (local) · AWS S3 (production) |
| Monorepo | Turborepo 2 · pnpm 10 |

---

## Architecture notes

- Backend owns all business logic. Frontend is presentation only.
- `@app/logic` Zod schemas are the contract — both sides validate against them; types are never duplicated.
- Backtests on ≤ 2 years of daily data run inline and return synchronously. Longer/heavier jobs go through Celery with polling.
- OHLCV data is cached in Redis (1h TTL) after the first fetch.
- Auth is optional — the app works fully without login; signing up persists strategies to the cloud.

---

## Docs

- Architecture & screen designs → `docs/superpowers/specs/2026-04-10-backtesting-app-design.md`
- Design system → `docs/design/design-principles.md`
- Tailwind tokens → `docs/design/tailwind-tokens.ts`
