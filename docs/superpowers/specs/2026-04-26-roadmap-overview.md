# Roadmap Overview — 2026-04-26

> Strategic direction for Q (the backtesting engine project).
> This document defines **what we're building toward and why**.
> Step-by-step execution plans live in sibling files (`*-phase-N-*.md`).

---

## Where we are (2026-04-26)

**What works:**

- Monorepo foundation (Turborepo + pnpm + Zod contracts in `@app/logic`).
- FastAPI backend with async SQLAlchemy 2, Alembic, Celery + Redis.
- `services/engines/{protocol,registry,simple}.py` — engine abstraction is in place.
- `services/data/{protocol,registry,providers}` — data abstraction is in place.
- Inline-vs-Celery routing in `routers/backtest.py` with graceful fallback.
- Golden-file regression test exists (`tests/test_golden_backtest.py`).

**What's missing (the honest list):**

1. **No data persistence — Redis-only 1h TTL.** A `BacktestRun` re-run a day later silently uses different bars. Every "regression" / "walk-forward" / "cross-engine" guarantee built on this is meaningless.
2. **Two SimpleEngine implementations** (`services/simple_engine.py` and `services/engines/simple.py`) coexist; routers import `EngineError` from the old path. Adding any new engine logic touches both.
3. **Alembic ↔ model drift.** `BacktestRun.metrics` and `celery_task_id` are declared on the model but never created by alembic; the app works only because `initdb.py` runs `Base.metadata.create_all`. Any fresh `alembic upgrade head` install ships a broken schema.
4. **Tests use `sqlite+aiosqlite`** while prod/dev use PostgreSQL — directly violates CLAUDE.md's "never mock the DB". JSON / timezone / `server_default=now()` semantics differ; this is exactly how (3) escaped detection.
5. **Engine registry silently downgrades** to SimpleEngine on `ImportError` and routes by **asset class** (wrong axis — VectorBT vs Backtrader is determined by strategy shape, not asset). Users can't tell which engine actually ran.
6. **Sandbox is a sieve.** `python_validator` blocks dunder attribute access but lets through `getattr(x, "__class__")`, `type(x).__subclasses__()`, `np.load(allow_pickle=True)`. Combined with `exec()`, this is RCE waiting to happen.
7. `services/engines/vectorbt.py` and `services/engines/backtrader.py` are stubs.
8. `MetricsOut` covers only 8 scalar metrics; no benchmark, no factor, no rolling stats.
9. `TradeOut` lacks `entry_time / exit_time / quantity / fees / slippage / mae / mfe`.
10. No commission / slippage / fill model — backtest results cannot be trusted.
11. No portfolio concept — single symbol, single timeframe only.
12. No walk-forward, no parameter optimization, no Monte Carlo.
13. No corporate-action handling, no survivorship-bias correction.
14. `services/data_ingestion.py` is dead code (the providers were rewritten under `services/data/providers/*.py`).
15. Mobile is skeleton-only (5 pages, no real API binding).
16. Results page shows 8 metrics + 1 chart — too thin for insight.

> Items 1-6 are foundation hazards that block every Phase 2 deliverable. They are addressed
> as **Task 0 (Foundation reset)** in `2026-04-26-phase-2-real-engine-and-quant-depth.md`,
> not deferred to a later phase.

---

## Strategic decisions

### 1. Engine strategy — hybrid, with a self-built escape hatch

| Engine                  | Role                                                                                                            | Status                                                              |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `SimpleEngine`          | Golden-file **arbiter**. Reference implementation for correctness checks; small enough to step through by hand. | Keep — the ground truth, not a fallback.                            |
| `VectorBTEngine`        | Vectorised path. Parameter sweeps, walk-forward, large-scale research.                                          | **Implement in Phase 2 (Task 4).**                                  |
| `BacktraderEngine`      | Event-driven path. Complex order types, multi-asset portfolios, broker bridge.                                  | **Implement in Phase 2 (Task 5).**                                  |
| `CustomEngine` (future) | Self-built when (and only when) the wrappers can no longer express what we need.                                | Reserve a slot in `protocol.py`. Do NOT build in the next 6 months. |

**Routing rule — by strategy shape, not asset class** (lives in `services/engines/registry.py`):

```
explicit engine_hint  → honoured or HTTP 422 (NEVER silently downgraded)
no hint, vectorisable → VectorBT  (fallback to Simple if not installed)
no hint, event-driven → Backtrader (fallback to Simple if not installed)
no hint, undetermined → Simple
```

**Honest-engine principle:** the API response always carries the engine that actually ran (`BacktestResult.engine`). Silent downgrades on user-supplied hints are a bug; they were the default in Phase 1 and are explicitly removed in Phase 2 Task 6.

### 2. Asset focus — three primary, portfolio second

**6-month primary scope:** US equities (daily + minute), A-shares (akshare), crypto (ccxt daily).
**6-month secondary scope:** Multi-asset portfolio at the **portfolio layer**, not the engine layer.
**Out of scope (6 months):** tick / orderbook data, futures/options, FX.

### 3. Realism — two tiers

**Tier 1 (must ship in Phase 2 — without this, results are noise):**

- Commission model (percentage / per-share / tiered).
- Slippage model (fixed bps / spread-based / volatility-based).
- Fill model (next-bar-open / current-close-with-delay / VWAP slice).
- Default parameters per asset class.

**Tier 2 (Phase 3-4):**

- Volume participation cap & market impact.
- Short-borrow cost & overnight financing.
- Corporate actions (splits, dividends, adjustments) — handled in the **data layer**, not the engine.
- Survivorship-bias correction (delisted-symbol data).
- Signal-to-fill latency model.

### 4. Strategy expression — three rails, one trunk, one contract

```
              ┌── Blocks (visual) ──────┐
              │                          │
  AI assistant ┤   all emit/edit ───────┼──> Python SDK (single contract) ──> Engine
              │                          │
              └── Direct Python ─────────┘
```

- **Python SDK is the trunk.** Make it powerful and ergonomic first; everything else generates or edits Python.
- **One strategy contract, three engines.** Every strategy returns the same dict shape (`run(ohlcv) -> {entries, exits, [stop_loss_pct, take_profit_pct, size_pct]}`). Defined once in `services/engines/strategy_contract.py`; every engine adapter reads from it. No engine-specific signature is allowed.
- **Blocks → Python is one-way.** Do not attempt round-trip sync; that's a tar pit.
- **AI is an editor assistant, not a one-shot generator.** Three operations: `explain`, `improve` (returns a diff), `complete` (inline). Every diff is validated by the AST validator before it can be saved. Users supply their own API key (BYOK); we don't store provider keys server-side by default.

### 5. Live trading & paper trading

- **Paper trading:** Phase 5 (month 5).
- **Live trading:** Phase 6 (month 6) — **read-only first** (positions, orders, account). No live order placement until a separate risk-review checklist is in place.

### 6. Sandboxing — landed in Phase 2 (Task 0.C)

- Strategy code runs in a **subprocess** with `resource.setrlimit(RLIMIT_CPU, RLIMIT_AS, RLIMIT_NOFILE)`, empty `env`, msgpack stdin/stdout, whitelisted imports (numpy / pandas / math).
- AST validator runs first as a fast-fail; subprocess is the second wall.
- **`RestrictedPython` rejected** — it cripples pandas attribute access; user experience for quant code becomes intolerable.
- API responses carry `sandbox: "subprocess" | "in_process"` so the actual mode is visible.
- Originally scheduled for Phase 5; pulled forward because (a) the AI assistant lands in Phase 2 and would otherwise feed code into a sieve, and (b) the open-source release in Phase 6 cannot ship with a known RCE.

---

## The three trunks

```
Spine (cross-cutting, every phase): contracts (@app/logic) + test pyramid + engine abstraction

  Trunk A · Engine realism      → results you can trust
  Trunk B · Analytical depth    → insight density per backtest
  Trunk C · Expression & UX     → the surface area people interact with
```

Every phase advances all three trunks; we never let one trunk lap the others by more than one phase.

---

## Phase map (6 months)

| Phase       | Window                                | Theme                                                         | Plan file                                           |
| ----------- | ------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------- |
| **Phase 1** | 2026-04-10 → 2026-04-25               | Scaffold (web + mobile + API + Docker + CI)                   | `2026-04-10-phase-1-scaffold.md`                    |
| **Phase 2** | **2026-04-26 → 2026-06-21 (8 weeks)** | **Real Engine + Quant Depth (showcase release)**              | `2026-04-26-phase-2-real-engine-and-quant-depth.md` |
| Phase 3     | 2026-06-22 → 2026-07-19 (4 weeks)     | Realism Tier 2 + multi-asset portfolio + Backtrader           | (to be written after Phase 2)                       |
| Phase 4     | 2026-07-20 → 2026-08-16 (4 weeks)     | Benchmark / factor attribution / regime analysis              | (to be written)                                     |
| Phase 5     | 2026-08-17 → 2026-09-13 (4 weeks)     | Sandbox hardening + paper trading                             | (to be written)                                     |
| Phase 6     | 2026-09-14 → 2026-10-11 (4 weeks)     | Read-only broker adapters + monitoring + production hardening | (to be written)                                     |

> Phase 2 is the **showcase phase** — the product becomes demoable to outsiders.
> Phases 3-6 are sketched here at the goal level only; each gets its own executable plan
> (in the style of `2026-04-10-phase-1-scaffold.md`) at the end of the previous phase.

---

## Phase 2 (8-week sprint) — at-a-glance

> Full executable plan: `2026-04-26-phase-2-real-engine-and-quant-depth.md`.
> Risk register: `2026-04-26-phase-2-risk-register.md`.

| Week    | Deliverable                                                                                                                                                                  | Why it matters                                                                                                                                                         |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1**   | **Task 0 — Foundation reset:** bitemporal OHLCV store + subprocess sandbox + engines re-org + alembic alignment + real-PG test infra + dead-code purge.                      | Every later Task assumes point-in-time replay, a single SimpleEngine, an honest registry, and real-DB tests. Without Task 0, every later "regression test" is theatre. |
| **2**   | `ExecutionModel` (commission + slippage + fill) + extended `TradeOut`/`MetricsOut` (16+ metrics) + `@app/logic` Zod sync + golden values rebuilt.                            | Backtests become trustworthy.                                                                                                                                          |
| **3**   | `VectorBTEngine` real implementation.                                                                                                                                        | 10× speedup unlocks weeks 5-6 optimization.                                                                                                                            |
| **3-4** | `BacktraderEngine` real implementation + registry by strategy shape (no silent fallback).                                                                                    | Tiered/per-share commissions and stop-loss become possible; engine choice is honest.                                                                                   |
| **4**   | Three-tier cross-engine golden agreement (Simple = arbiter; Tier 1 trade-sequence strict; Tier 2 returns/risk 2%; Tier 3 ratios 5%).                                         | First proof that all three engines agree on the same strategy.                                                                                                         |
| **5-6** | `services/analytics/walk_forward.py` + `optimization.py` (grid) + Celery + `/optimizations` route + web optimization page (ECharts heatmap / parallel coords / WF timeline). | First quant-grade headline feature.                                                                                                                                    |
| **7**   | Results page rebuild (16-metric grid, equity, underwater, rolling Sharpe, monthly heatmap, trade scatter, top-10 drawdowns).                                                 | Insight density per backtest.                                                                                                                                          |
| **7**   | AI assistant in the editor (BYOK; explain / improve / complete; validator-gated diffs).                                                                                      | Lowers barrier without lying about correctness.                                                                                                                        |
| **8**   | Mobile MVP wired to API + Expo push notifications on Celery completion.                                                                                                      | Cross-platform parity.                                                                                                                                                 |
| **8**   | CI gates (≥ 60% coverage, schema-diff, lint, typecheck, E2E) + fresh-machine drill + `v0.2.0` tag + Phase 3 plan written.                                                    | Release & continuity.                                                                                                                                                  |

**Phase 2 exit criteria** (the demo script):

1. **Trustworthy backtest:** one-click BTCUSDT 2020-2024 daily → < 5 s → 16+ metrics + equity + drawdown + monthly heatmap. Re-running 30 days later returns identical metrics.
2. **Engine choice is honest:** the same strategy run with `engine_hint="vectorbt" | "backtrader" | "simple"` returns three results within Tier-2 tolerance (≤ 2% on Sharpe / CAGR / max drawdown). Response carries the actual engine.
3. **Walk-forward optimization:** 10×10 SMA grid → background Celery → heatmap with IS/OOS bars and parameter-stability indicator.
4. **AI assistant in the editor:** "explain this code" / "add an RSI filter" works inline in Monaco with BYOK.
5. **Mobile parity:** same run visible on mobile, push notification on Celery completion.

---

## Phase 3 sketch — Realism Tier 2 + Multi-asset portfolio

> Backtrader and the data store landed in Phase 2 — Phase 3 builds **on top** of them.

- `services/portfolio/` — capital allocation, rebalancing, correlation constraints; multi-symbol `BacktestRun`.
- `services/data/adjustments.py` — splits / dividends / adjusted close, applied at the bitemporal store layer (so a run's `as_of_time` still gives byte-identical results).
- `services/data/corporate_actions.py` — survivorship-bias corrected universe for US equities (delisted-symbol persistence).
- Volume-participation `FillModel` (cap = N% of bar volume) + market-impact model.
- Short-borrow + overnight-financing cost models in `ExecutionConfig`.
- `services/analytics/monte_carlo.py` — trade-bootstrap confidence bands.
- `ohlcv_bars` table partitioning + `compress_history()` job (R5 mitigation).

## Phase 4 sketch — Benchmark / Factor / Regime

- Auto-fetched benchmarks (SPY, QQQ, 000300.SH, BTC) → alpha / beta / IR / tracking error.
- `services/analytics/factors.py` — Fama-French 3/5, custom factor registration.
- `services/analytics/regime.py` — HMM or volatility-quantile regime tagging; per-regime metrics.
- Web Risk tab — VaR / CVaR / factor exposure radar / regime timeline.

## Phase 5 sketch — Paper trading

> Sandbox already landed in Phase 2 (Task 0.C); Phase 5 is purely about live data + virtual fills.

- `services/live/` — streaming-bar adapter (ccxt websocket, polygon websocket).
- Strategy code runs unchanged inside the existing subprocess sandbox; input swaps from historical bars to streaming bars.
- Virtual account uses the same `ExecutionModel` from Phase 2 (with paper-trading-specific defaults — wider slippage, tighter latency).
- New router `POST /paper-sessions`, mobile push on fills.
- `services/analytics/live_attribution.py` — real-time vs backtest divergence tracking (alpha decay diagnostics).

## Phase 6 sketch — Broker adapters (read-only) + production hardening + open-source release

- `services/broker/protocol.py`, `AlpacaAdapter`, `BinanceAdapter` — **read-only**.
  - Account, positions, orders, fills query.
  - **No order placement** in this phase.
- Sentry + structured logging + Celery task metrics.
- CI coverage tightened from Phase 2's 60% floor: `apps/api` ≥ 80%, `@app/logic` ≥ 95%.
- Per-user rate limits on backtest runs and optimization jobs.
- Open-source release: contributor guide, plugin API docs, security disclosure policy, sample-strategy gallery.

---

## Cross-cutting infrastructure decisions (apply to every phase)

These do not belong to any single phase but are settled once and obeyed forever.

### a. Schema versioning

- Add `schema_version: int` to `BacktestRun.metrics` and `BacktestRun.trades` in DB.
- `MetricsOut` / `TradeOut` carry the same field.
- Web/mobile renderers read `schema_version` and choose the appropriate component.
- **Rule:** never silently mutate the shape of an existing version; always bump.

### b. Data layer — bitemporal OHLCV store (lands Phase 2 Task 0.A)

- **Bitemporal model**: `ohlcv_bars(symbol, source, timeframe, ts, effective_from)` composite PK; `effective_to` nullable. Append-only — upstream corrections close the previous row and insert a new one; **never UPDATE** historical rows.
- Every `BacktestRun` and `OptimizationRun` records `as_of_time`. Reads filter by `effective_from ≤ as_of_time < (effective_to OR ∞)` → byte-identical replay regardless of when run.
- Redis is downgraded to a **hot-path accelerator** keyed on the store query hash, never source of truth.
- Provider call path: `read_bars(as_of)` → if covered, return; else `_fetch_upstream(missing_range)` → `write_bars(...)` → `read_bars(now())`.
- Phase 3 adds partitioning + `compress_history()` once `ohlcv_bars` crosses 50M rows or query latency exceeds 500 ms (R5).

### c. Engine contract

- `services/engines/protocol.py` exposes a single `BacktestEngine` Protocol.
- All engines (Simple, VectorBT, Backtrader, future Custom) implement it.
- `BacktestResult` is the only output type — engines never leak their native result objects past the protocol boundary.

### d. Test pyramid (non-negotiable)

- **`@app/logic`** → unit, no I/O.
- **Engines** → three-tier golden-file regression (one strategy file, all engines run it):
  - **Tier 1 (strict)**: `(entry_bar, exit_bar, side)` trade sequence byte-identical.
  - **Tier 2 (rel 2%)**: returns / risk metrics — `cagr`, `total_return`, `sharpe_ratio`, `max_drawdown`, `volatility`.
  - **Tier 3 (rel 5%)**: ratio metrics — `win_rate`, `profit_factor`, `calmar_ratio`, `omega_ratio`, `tail_ratio`.
  - **SimpleEngine is the arbiter** — when a tier fails, trust SimpleEngine, debug the other adapter.
- **API routes** → integration tests against **real PostgreSQL** (testcontainers). `sqlite+aiosqlite` is forbidden. CLAUDE.md mandates this; Phase 1 violated it; Phase 2 Task 0.E fixes it.
- **Web critical flows** → Playwright E2E.
- **Schema diff** → `tests/test_schema_diff.py` runs `alembic upgrade head` against an empty PG and asserts zero diff against `Base.metadata`. CI gate on every PR.
- **Sandbox** → known-escape suite (`getattr.__class__`, `type.__subclasses__`, `np.load(allow_pickle)`, CPU/AS limits).
- Every new metric → at least one hand-computed unit test + a golden assertion at the right tier.
- Every new engine → reuses the single golden strategy fixture; tolerances above are non-negotiable without an entry in `docs/engines/known-discrepancies.md`.

### e. Frontend chart library

- Recharts is sufficient through Phase 2 weeks 1-4.
- **Phase 2 week 5 introduces `echarts-for-react`** for heatmaps, parallel coordinates, and tree/sankey diagrams.
- Both libraries coexist; Recharts stays for simple line/bar; ECharts handles dense analytics.

### f. Dependency policy

- Pin exact versions in `pyproject.toml` and `package.json`. Range-only pinning (`>=`) is permitted for transitive scientific deps where vectorbt itself is the constraint (e.g., `numpy>=1.26,<2.0`).
- VectorBT + Backtrader install via `pip install -e ".[engines]"`; sandbox runtime via `".[sandbox]"`.
- Document the install path in each phase's plan.

### g. Honest engine routing (lands Phase 2 Task 6)

- Explicit `engine_hint` is **never silently downgraded**. If the requested engine is unavailable, the API returns `422 EngineUnavailable` with the install command to fix it.
- Auto-routing (no hint) may fall back to SimpleEngine, but the response always echoes `engine: "simple"` so the caller knows what ran.
- Routing is by **strategy shape** (vectorisable vs event-driven), not asset class. The shape detector lives in `services/engines/strategy_shape.py`.

### h. Sandbox-by-default (lands Phase 2 Task 0.C)

- Strategy execution defaults to subprocess sandbox. The in-process path exists only for trusted internal call-sites (the SimpleEngine arbiter, benchmarks).
- API responses carry `sandbox: "subprocess" | "in_process"` so users can see what ran.
- The AST validator is the **first** wall (fast-fail before subprocess spawn); the subprocess + `setrlimit` is the **second** wall.

### i. AI assistant key handling (lands Phase 2 Task 12)

- BYOK: users supply their own LLM API key per request via `X-LLM-Provider` + `X-LLM-Api-Key` headers.
- Server is stateless w.r.t. keys by default — never logged, never persisted. Optional opt-in for server-managed keys lands no earlier than Phase 6 (with explicit user consent + at-rest encryption).
- Every AI-generated diff is run through the AST validator before it can be saved.

---

## What we explicitly will NOT build (in 6 months)

- A custom event-driven engine from scratch. (Phase 7+ at earliest.)
- Tick-level / orderbook backtesting. (Wait until a real strategy needs it.)
- Live order placement. (Phase 7+ at earliest, after sandbox + risk review.)
- A strategy marketplace. (Mentioned as an extension point only; no UI.)
- Self-hosted LLM. (Use OpenAI / DeepSeek / any HTTP provider.)
- Round-trip blocks ↔ Python sync.
- Mobile strategy editor (read-only viewer is fine).

---

## Operating rhythm

- **Each phase ends with a tagged release** (`v0.2.0`, `v0.3.0`, ...).
- **Each phase starts with the next phase plan written first** — no code before plan.
- **Each plan follows the Phase 1 format**: Task → Step → verifiable output + commands.
- **Showcase moments** (Phase 2 end, Phase 5 end, Phase 6 end) include a recorded demo and a written changelog.
