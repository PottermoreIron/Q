# Phase 2 — Real Engine & Quant Depth (8-week sprint)

> Window: 2026-04-26 → 2026-06-21 (8 weeks).
> Strategy context: see `2026-04-26-roadmap-overview.md`.
> Risks: see `2026-04-26-phase-2-risk-register.md`.
> Format follows `2026-04-10-phase-1-scaffold.md`: Task → Step → verifiable output + commands.

---

## Operating model (read this first)

**Workforce:** the human reviews and steers; agents implement. Calendar is 8 weeks; review-bandwidth is the bottleneck, not implementation throughput.

**Non-negotiable principles:**

1. **No silent fallbacks.** A user-facing `engine_hint` that can't be honoured returns `422`, never quietly downgrades. The chosen engine is always echoed back in the response.
2. **No mock-PostgreSQL.** Tests run against real PostgreSQL (Docker). `sqlite+aiosqlite` is removed in Task 0.E. CLAUDE.md already mandates this; current code violates it.
3. **No new code on shaky foundations.** Task 0 (foundation reset) lands before any other Task starts. If Task 0 slips into Week 2, scope is cut from the _other end_ (Tasks 12, 13) — never from Task 0.
4. **Reproducible by construction.** Every backtest is bound to an `as_of_time`. Re-running a year-old run on today's binary returns byte-identical metrics.

---

## Phase exit criteria (the demo script)

A fresh `git clone` + `docker compose up -d` + `pnpm install` + `pnpm dev` must reach all five within 3 minutes of demo:

1. **Trustworthy backtest:** one-click run on BTCUSDT 2020-2024 daily → < 5 s → 16+ metrics + equity curve + drawdown + monthly heatmap. The same run started on day N+30 returns identical metrics (point-in-time replay).
2. **Engine choice is honest:** the same strategy run with `engine_hint="vectorbt"`, `"backtrader"`, `"simple"` returns three results within Tier-2 tolerance (≤ 2% on Sharpe / CAGR / max drawdown). The response carries the actual engine that ran.
3. **Walk-forward optimization:** 10×10 SMA grid → background Celery → returns to a heatmap with IS/OOS bars and parameter-stability indicator.
4. **AI assistant in the editor:** "explain this code", "add an RSI filter to this strategy" — works inline in the Monaco editor with BYOK (user-supplied API key, never stored server-side by default).
5. **Mobile parity:** the same run is visible on mobile, push notification fires when the Celery job completes.

---

## Task layout

| Task       | Theme                                                                                     | Weeks |
| ---------- | ----------------------------------------------------------------------------------------- | ----- |
| **Task 0** | **Foundation reset (data store · sandbox · engines re-org · alembic align · test infra)** | **1** |
| Task 1     | `ExecutionModel` (commission / slippage / fill)                                           | 2     |
| Task 2     | Extend `TradeOut` and `MetricsOut` (+ `services/metrics.py`)                              | 2     |
| Task 3     | `@app/logic` Zod sync + golden-test rebuild                                               | 2-3   |
| Task 4     | `VectorBTEngine` real implementation                                                      | 3     |
| Task 5     | `BacktraderEngine` real implementation                                                    | 3-4   |
| Task 6     | Engine registry: routing by **strategy shape**, no silent fallback                        | 4     |
| Task 7     | Cross-engine golden agreement (three-tier assertion)                                      | 4     |
| Task 8     | `services/analytics/` — walk-forward + grid optimization                                  | 5     |
| Task 9     | Optimization REST routes + Celery wiring                                                  | 5-6   |
| Task 10    | Web optimization page + `echarts-for-react` introduction                                  | 6     |
| Task 11    | Web results page rebuild (16 metrics, underwater, monthly heatmap, trade scatter)         | 7     |
| Task 12    | AI assistant in the editor (BYOK, swappable provider)                                     | 7     |
| Task 13    | Mobile MVP wiring + push notifications                                                    | 8     |
| Task 14    | CI gates + Phase 2 release (`v0.2.0`)                                                     | 8     |

---

## Task 0 — Foundation reset (Week 1, hard prerequisite)

> Six sub-tasks, all merged before Task 1+ starts. Independently shippable; can be parallelised across agents.

### 0.A · Bitemporal OHLCV store

**Why:** today, `services/data/protocol.py` writes to Redis with TTL=3600 s only. Re-running an old `BacktestRun` after a day silently uses different data. Walk-forward, golden tests, and cross-engine comparisons are meaningless without point-in-time replay.

**Files:**

- Create: `apps/api/models/ohlcv_bar.py`
- Create: `apps/api/alembic/versions/0005_create_ohlcv_bars_table.py`
- Create: `apps/api/services/data/store.py`
- Modify: `apps/api/services/data/protocol.py` (cache becomes opt-in accelerator only)
- Modify: every `apps/api/services/data/providers/*.py` (write-through to store)
- Create: `apps/api/tests/test_ohlcv_store.py`

- [ ] **Step 1: Schema** — bitemporal: `(symbol, source, timeframe, ts, effective_from)` composite PK; OHLCV + `adj_close` + `volume`; `fetched_at`; `effective_to` nullable, indexed.

- [ ] **Step 2: Repository** — `read_bars(..., as_of)` for point-in-time queries; `write_bars(...)` is append-only: identical → no-op; changed → close the open row (`effective_to = fetched_at`) and insert a new one.

- [ ] **Step 3: Provider integration** — providers become thin upstream wrappers: `read_bars(as_of)` → if covered, return; else fetch upstream, `write_bars(...)`, `read_bars(now())`. Redis `cache_get/cache_set` survives only as a hot-path accelerator keyed on the store query hash.

- [ ] **Step 4: BacktestRun gets `as_of_time`** — column on `BacktestRun`; `POST /backtests` writes `now()` and threads it through. Add `GET /backtests/{id}/replay` that re-runs with the same `as_of_time` and asserts identical metrics.

- [ ] **Step 5: Tests** — same `(symbol, ts)` written twice identically → no new row; written with different `close` → previous row closed, new row inserted; `as_of=T` returns rows where `effective_from ≤ T < (effective_to OR ∞)`; simulated upstream correction does not change a historical run's read.

```bash
pytest tests/test_ohlcv_store.py -v
```

---

### 0.B · Engines re-org and strategy contract

**Why:** today there are two SimpleEngine implementations (`services/simple_engine.py` and `services/engines/simple.py`) and `EngineError` is imported from the old path. Adding `ExecutionModel` to this is a minefield.

**Files:**

- Move: `services/simple_engine.py` → contents merged into `services/engines/_runtime.py` and `services/engines/simple.py`
- Create: `services/engines/strategy_contract.py` (single source of truth)
- Create: `services/engines/exceptions.py` (new home for `EngineError`, `EngineUnavailable`)
- Modify: `routers/backtest.py`, `services/tasks.py` (update imports)
- Delete: `services/simple_engine.py` after refs are gone
- Modify: `services/block_compiler.py` (emit code matching the contract)

- [ ] **Step 1: Lock the contract.** `strategy_contract.py` documents and validates:

```python
def run(ohlcv: pd.DataFrame) -> dict:
    return {
        "entries":         pd.Series[bool],   # required
        "exits":           pd.Series[bool],   # required
        "stop_loss_pct":   float | None,      # optional
        "take_profit_pct": float | None,      # optional
        "size_pct":        float | None,      # optional, default 1.0
    }
```

All three engine adapters and `block_compiler` agree on this single dict shape — no engine-specific signature is allowed.

- [ ] **Step 2: Move runtime.** `_runtime.py` owns `_simulate`, `_bars_to_df`, `_infer_bars_per_year`, `_sample_equity`. `simple.py` becomes a 30-line adapter calling `_runtime`.

- [ ] **Step 3: Update imports.** Every reference to `services.simple_engine` is replaced. Verify with `grep`:

```bash
grep -rn "services.simple_engine" apps/api/   # must return nothing
```

Then delete `services/simple_engine.py`.

- [ ] **Step 4: block_compiler emits the contract.** Currently leaves `stop_loss_pct` as a free variable — that's a contract violation. Fix to return it inside the dict.

- [ ] **Step 5: Tests** — existing `test_strategy.py`, `test_backtest.py`, `test_golden_backtest.py` must still pass after the move (pure refactor; semantics unchanged).

---

### 0.C · Subprocess sandbox

**Why:** C1 was answered (b) — sandbox lands in Phase 2, not Phase 5. Current `_SAFE_BUILTINS` + AST validator misses `getattr(obj, "__class__")`, `type(...).mro()`, `np.load(allow_pickle=True)`. RestrictedPython is not chosen — it cripples pandas. Subprocess + `setrlimit` is the production-grade answer.

**Files:**

- Create: `apps/api/sandbox/runner.py` (subprocess entry point)
- Create: `apps/api/services/engines/sandbox.py` (parent-side client)
- Modify: `services/engines/_runtime.py` (sandbox is the default)
- Create: `apps/api/tests/test_sandbox.py`

- [ ] **Step 1: Runner.** Reads msgpack from stdin (`{"code", "ohlcv", "limits"}`); calls `resource.setrlimit(RLIMIT_CPU, RLIMIT_AS, RLIMIT_NOFILE)`; re-runs the AST validator; execs strategy with whitelisted imports (`numpy`, `pandas`, `math` only); writes msgpack result to stdout. Spawned with `env={}`.

- [ ] **Step 2: Client.** `SandboxClient(cpu_s=30, mem_mb=2048).run(code, bars)`; uses `asyncio.create_subprocess_exec`; hard-kills on timeout. Use `multiprocessing.get_context("forkserver")` worker pool to amortise cold-start (see R3).

- [ ] **Step 3: Runtime delegates.** `_runtime.run_strategy(code, df, *, sandbox=True)` is the new signature. `sandbox=False` only allowed from trusted internal call-sites (benchmarks, the SimpleEngine arbiter); API responses always carry `sandbox: "subprocess" | "in_process"` so the actual mode is visible.

- [ ] **Step 4: Tests** — known escapes blocked:

```python
# All must raise SandboxError or ValidationError:
"getattr(close, '__class__').__bases__"
"type(0).__subclasses__()"
"import numpy; numpy.load(b'...', allow_pickle=True)"
"while True: pass"            # CPU limit kills it
"x = bytearray(3 * 1024**3)"  # AS limit kills it
```

```bash
pytest tests/test_sandbox.py -v
```

---

### 0.D · Alembic alignment

**Why:** `models/backtest_run.py` declares `metrics`, `celery_task_id`; alembic 0003/0004 never created them. The app works only because `initdb.py` runs `Base.metadata.create_all(...)`. Any fresh install via `alembic upgrade head` ships a broken schema.

**Files:**

- Create: `apps/api/alembic/versions/0006_align_backtest_runs_with_model.py`
- Create: `apps/api/tests/test_schema_diff.py`

- [ ] **Step 1: Add missing columns.**

```python
def upgrade() -> None:
    op.add_column("backtest_runs", sa.Column("metrics",        sa.JSON(),    nullable=True))
    op.add_column("backtest_runs", sa.Column("celery_task_id", sa.String(255), nullable=True))
    op.add_column("backtest_runs", sa.Column("as_of_time",     sa.DateTime(timezone=True),
                                              server_default=sa.text("now()"), nullable=False))
```

- [ ] **Step 2: Schema-diff CI gate.** `test_schema_diff.py` runs `alembic upgrade head` against an empty PG container and asserts `alembic.autogenerate.compare_metadata(...)` returns no diffs. CI runs this on every PR — would have caught the original omission immediately.

---

### 0.E · Real-PostgreSQL test infrastructure

**Why:** CLAUDE.md mandates "FastAPI routes → integration tests against real PostgreSQL. Never mock the DB". Current tests use `sqlite+aiosqlite:///:memory:`. JSON semantics, datetime tz handling, `server_default=now()` all differ — exactly the gap that 0.D exposed.

**Files:**

- Modify: `apps/api/pyproject.toml` (add `testcontainers[postgresql]` to `[dev]`)
- Create: `apps/api/tests/conftest.py` (session-scoped PG fixture)
- Modify: every `tests/test_*.py` that hardcoded `TEST_DB_URL = "sqlite+aiosqlite:///..."`
- Delete: `apps/api/initdb.py`

- [ ] **Step 1: conftest.** `pg_container` (session scope) starts `postgres:15-alpine`; `db_engine` (session) runs `alembic upgrade head` once; `db` (per-test) opens a session and truncates all tables on teardown.

- [ ] **Step 2: Replace sqlite refs.**

```bash
grep -rn "sqlite+aiosqlite" apps/api/tests/   # must be empty after this step
```

- [ ] **Step 3: Delete `initdb.py`** — exists only to bypass alembic for SQLite. With real PG, alembic works; the file is dead weight.

- [ ] **Step 4: Performance budget.** Full `pytest -q` < 5 minutes locally. If exceeded, switch to `pytest-xdist` (R7).

---

### 0.F · Delete dead code · pin deps · Task 0 commit

- [ ] **Step 1: Delete `services/data_ingestion.py`** after `grep -rn "from services.data_ingestion" apps/api/` returns empty.
- [ ] **Step 2: Pin engine deps.**

```toml
engines = [
  "vectorbt==0.26.2",
  "backtrader==1.9.78.123",
  "numba>=0.59,<0.60",
  "numpy>=1.26,<2.0",
]
sandbox = ["msgpack>=1.0.7"]
```

- [ ] **Step 3: Commit.**

```bash
git commit -m "feat(foundation): bitemporal OHLCV store, sandbox, engines re-org, alembic align, real-pg tests"
```

**Exit gate (must pass before Task 1 starts):**

- `pytest -q` green against real PG.
- `alembic upgrade head` against empty DB → `test_schema_diff.py` passes.
- A backtest run can be replayed with byte-identical metrics.
- `getattr(obj, "__class__")` is rejected by sandbox.
- `grep` proves: no `simple_engine.py`, no `data_ingestion.py`, no `initdb.py`, no `sqlite+aiosqlite`.

---

## Task 1 — ExecutionModel (commission · slippage · fill)

**Files:**

- Create: `apps/api/services/engines/execution_model.py`
- Modify: `apps/api/services/engines/_runtime.py`
- Modify: `apps/api/services/engines/simple.py`
- Create: `apps/api/tests/test_execution_model.py`

- [ ] **Step 1: Failing tests** — every concrete model has a hand-computable assertion:
  - `PercentageCommission(rate=0.001)` on $10,000 notional → $10.
  - `PerShareCommission(per_share=0.005, min_per_order=1.0)` on 100 shares → $1 (min applied).
  - `TieredCommission([(0,100,0.001),(100,None,0.0005)])` on 200 shares @ $50 → tiered correctly.
  - `FixedBpsSlippage(bps=5)` on $100 buy → $100.05; sell symmetric.
  - `SpreadSlippage(half_spread_bps=2)` symmetric.
  - `VolatilitySlippage(atr_multiplier=0.1)` consumes precomputed ATR.
  - `NextBarOpenFill` — signal at bar t fills at bar t+1 open.
  - `CurrentCloseDelayedFill(latency_bars=1)`.
  - `VWAPSliceFill` — one-bar VWAP approximation.
  - `default_for_asset_class("a_share")` applies 0.1% stamp duty on **sells only**.

- [ ] **Step 2: Implement** the three Protocols (`CommissionModel`, `SlippageModel`, `FillModel`), all concrete classes, `ExecutionConfig` dataclass, and `default_for_asset_class(asset_class)`:
  - `us_equity` → 0.05% commission · 1 bp slippage · next-bar-open fill.
  - `a_share` → 0.025% + 0.1% stamp on sells · 2 bp slippage · next-open.
  - `crypto` → 0.1% commission · 2 bp slippage · current-close-delayed.
  - `forex` → 0 commission · 0.5 pip slippage · next-open.

- [ ] **Step 3: Wire into `_runtime`.** `_simulate` now delays signal-to-fill by `fill.latency_bars`, computes fill price via `fill.fill_price(...)`, adjusts via `slippage.adjust(...)`, computes `commission.fee(...)` per leg, and records `fees` and `slippage_cost` separately on every trade record.

- [ ] **Step 4: Commit.**

```bash
git commit -m "feat(engine): ExecutionModel — commission, slippage, fill"
```

---

## Task 2 — Extend `TradeOut` and `MetricsOut`

**Files:** `schemas/backtest_run.py`, `services/metrics.py`, `services/engines/_runtime.py`, `tests/test_metrics_extended.py`.

- [ ] **Step 1: TradeOut (schema_version=2)** — add `entry_time`, `exit_time`, `quantity`, `pnl_pct`, `fees`, `slippage_cost`, `bars_held`, `mae`, `mfe`. `side` becomes `Literal["long","short"]`.

- [ ] **Step 2: MetricsOut (schema_version=2)** — 4 groups:
  - **Returns**: `cagr`, `total_return`, `final_value`.
  - **Risk**: `volatility`, `downside_volatility`, `max_drawdown`, `max_drawdown_duration_days`, `var_95`, `cvar_95`.
  - **Risk-adjusted**: `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `omega_ratio`, `tail_ratio`.
  - **Trade quality**: `total_trades`, `win_rate`, `profit_factor`, `avg_win`, `avg_loss`, `largest_win`, `largest_loss`, `avg_trade_duration_bars`.
  - **Exposure**: `exposure_pct`, `turnover`.

- [ ] **Step 3: services/metrics.py** — numpy + pandas only. Each new metric has a docstring with the formula. Key formulas:

```
calmar     = cagr / abs(max_drawdown)
omega(t=0) = sum(returns > t) / abs(sum(returns < t))
tail_ratio = quantile(returns, 0.95) / abs(quantile(returns, 0.05))
var_95     = -quantile(returns, 0.05)
cvar_95    = -mean(returns[returns <= quantile(returns, 0.05)])
```

- [ ] **Step 4: Hand-computed tests** — for each new metric, hand-compute on a 5-10 element series and assert.

- [ ] **Step 5: Update golden values** — re-run the golden fixture with default `ExecutionConfig`, capture the new metric set into `tests/fixtures/golden_metrics.json`, commit.

```bash
pytest tests/test_metrics_extended.py tests/test_golden_backtest.py -v
git commit -m "feat(metrics): extend TradeOut and MetricsOut with risk and trade-quality fields"
```

---

## Task 3 — `@app/logic` Zod sync + golden test rebuild

**Files:** `packages/logic/src/types/backtest.ts`, `apps/web/src/lib/api.ts`, `apps/api/tests/test_golden_backtest.py`.

- [ ] **Step 1: Zod mirrors Python.**

```ts
// Wire format: snake_case (Pydantic). TS surface: camelCase.
// Single transformer in apps/web/src/lib/api.ts.
export const Metrics = z.object({
  schemaVersion: z.literal(2).default(2),
  cagr: z.number().nullable() /* ... */,
});
export const Trade = z.object({
  schemaVersion: z.literal(2).default(2),
  entryTime: z.string() /* ... */,
});
export const EngineHint = z
  .enum(["simple", "vectorbt", "backtrader"])
  .optional();
```

- [ ] **Step 2: Single transformer.** `snakeToCamel` / `camelToSnake` pair in `apps/web/src/lib/api.ts`, used by every fetch wrapper. No ad-hoc renaming inside components.

- [ ] **Step 3: Build & test.**

```bash
pnpm --filter @app/logic build && pnpm --filter @app/logic test
git commit -m "feat(logic): sync Metrics/Trade Zod schemas with backend v2"
```

---

## Task 4 — VectorBTEngine real implementation

**Files:** `services/engines/vectorbt.py`, `tests/test_vectorbt_engine.py`.

- [ ] **Step 1: Install + version probe.**

```bash
cd apps/api && pip install -e ".[engines]"
python -c "import vectorbt as vbt, numpy as np; print(vbt.__version__, np.__version__)"
# expected: 0.26.2  1.26.x
```

- [ ] **Step 2: Adapter unpacks the contract dict.** Strategy still returns `{"entries", "exits", "stop_loss_pct", "take_profit_pct"}`; the adapter calls `vbt.Portfolio.from_signals(close, entries, exits, sl_stop=..., tp_stop=..., fees=cfg.commission.rate, slippage=cfg.slippage.bps_equivalent()/1e4, freq=_infer_freq(df))`.

- [ ] **Step 3: Reject incompatible execution configs.**

```python
if not isinstance(cfg.commission, PercentageCommission):
    raise EngineError("VectorBT supports PercentageCommission only. Use BacktraderEngine for tiered/per-share.")
```

- [ ] **Step 4: `_portfolio_to_result`** populates the **same** `MetricsOut` and `TradeOut` shape as SimpleEngine. Where VectorBT's native metric exists, use it; missing ones recompute from `portfolio.returns()`.

- [ ] **Step 5: Speed sanity.** `pytest -m benchmark tests/test_vectorbt_engine.py::test_speedup_vs_simple` — on 5,000 bars, ≥ 10× faster than SimpleEngine. If not, perf bug — do not ship.

- [ ] **Step 6: Commit.**

```bash
git commit -m "feat(engine): VectorBTEngine real implementation"
```

---

## Task 5 — BacktraderEngine real implementation

**Why:** B2 picked (a) — both engines in Phase 2. Backtrader covers what VectorBT can't: tiered commissions, per-share fees, complex order types, multi-asset (Phase 3 ready).

**Files:** `services/engines/backtrader.py`, `tests/test_backtrader_engine.py`.

- [ ] **Step 1: Strategy adapter.** A `_SignalDrivenStrategy(bt.Strategy)` reads precomputed `entries[i]` / `exits[i]` in `next()` and calls `self.buy()` / `self.close()`. Stop-loss / take-profit map to `bt.Order.Stop` / `Limit` orders submitted alongside the entry.

- [ ] **Step 2: Commission / slippage mapping.** Map every `ExecutionConfig`:
  - `PercentageCommission(rate=r)` → `cerebro.broker.setcommission(commission=r)`.
  - `PerShareCommission` → custom `bt.CommInfoBase` subclass.
  - `TieredCommission` → custom `CommInfoBase` walking the tier list.
  - `FixedBpsSlippage(bps=b)` → `cerebro.broker.set_slippage_perc(perc=b/1e4)`.

- [ ] **Step 3: Tests.** Same SMA-cross fixture as VectorBT; tiered commission produces expected fees on a synthetic 200-share trade; stop-loss is honoured.

- [ ] **Step 4: Commit.**

```bash
git commit -m "feat(engine): BacktraderEngine real implementation"
```

---

## Task 6 — Engine registry: routing by strategy shape, no silent fallback

**Why:** today's registry routes by **asset class** (`crypto → VectorBT, else → Backtrader`) and **silently falls back to Simple** on `ImportError`. Both wrong:

- VectorBT vs Backtrader is determined by **strategy shape** (vectorisable vs needs an event loop), not asset.
- Silent fallback violates the "honest engine" principle (Operating model rule 1).

**Files:** `services/engines/registry.py`, `services/engines/strategy_shape.py`, `schemas/backtest_run.py` (add `engine_hint`), `routers/backtest.py`, `tests/test_engine_routing.py`.

- [ ] **Step 1: Strategy shape detector.**

```python
# services/engines/strategy_shape.py
def detect_shape(strategy_dict: dict) -> Literal["vectorisable", "event_driven"]:
    """'event_driven' if stop_loss_pct / take_profit_pct / size_pct present; else 'vectorisable'."""
```

- [ ] **Step 2: Registry — explicit hint never falls back.**

```python
def get_engine(*, hint: str | None, shape: str | None = None) -> BacktestEngine:
    if hint:
        try:    return _engines[hint]()
        except ImportError as e:
            raise EngineUnavailable(hint, str(e)) from e   # → HTTP 422
    if shape == "vectorisable":
        try:    return VectorBTEngine()
        except ImportError: return SimpleEngine()
    if shape == "event_driven":
        try:    return BacktraderEngine()
        except ImportError: return SimpleEngine()
    return SimpleEngine()
```

Auto-routing may fall back to Simple (with the response telling the truth via `result.engine`). Explicit `engine_hint` never falls back — `EngineUnavailable` becomes a 422 via FastAPI exception handler.

- [ ] **Step 3: Routing matrix tests** — every cell of `{hint × installed × shape}` has an assertion. Critical ones:
  - `hint="vectorbt"`, vectorbt missing → 422. **Not** Simple.
  - `hint=None`, shape vectorisable, vectorbt installed → VectorBT.
  - `hint=None`, shape event_driven, backtrader missing → Simple, response carries `engine="simple"`.

- [ ] **Step 4: Response carries actual engine.** Already supported (`BacktestResult.engine` is set by the engine, persisted to `BacktestRun.engine`). Add an explicit assertion in `tests/test_backtest.py` that the API echoes it.

- [ ] **Step 5: Commit.**

```bash
git commit -m "feat(engine): registry routes by strategy shape; hint never silently falls back"
```

---

## Task 7 — Cross-engine golden agreement (three-tier assertion)

**Why:** D1 best practice. Engine-level byte equality is unrealistic; 5% Sharpe divergence is dangerous. Three-tier assertion gives sharp signal without false alarms.

**Files:** `tests/test_golden_backtest.py`, `tests/fixtures/golden_strategy.py`, `tests/fixtures/golden_bars.json`, optionally `docs/engines/known-discrepancies.md` (only if R2 escalates).

- [ ] **Step 1: Single strategy, three engines.**

```python
@pytest.mark.parametrize("engine_factory", [SimpleEngine, VectorBTEngine, BacktraderEngine])
async def test_golden_three_engines_agree(engine_factory):
    bars     = load_golden_bars()
    code     = load_golden_strategy()           # one file, contract-conformant, runs everywhere
    result   = await engine_factory().run(code, bars)
    expected = load_baseline_metrics()          # recorded from SimpleEngine — the arbiter
    _assert_three_tier(result, expected)
```

- [ ] **Step 2: Three-tier assertion.**
  - **Tier 1 (strict):** trade sequence — `(entry_bar_idx, exit_bar_idx, side)` tuples must match exactly. Failure means a logic bug, not a numerical bug.
  - **Tier 2 (rel 2%):** `cagr`, `total_return`, `sharpe_ratio`, `max_drawdown`, `volatility`.
  - **Tier 3 (rel 5%):** `win_rate`, `profit_factor`, `calmar_ratio`, `omega_ratio`, `tail_ratio` — ratio metrics are more sensitive to small-N effects.

- [ ] **Step 3: SimpleEngine is the arbiter.** When a tier fails: trust SimpleEngine, debug the other adapter. Document in the test file's docstring.

- [ ] **Step 4: Commit.**

```bash
git commit -m "test(engine): three-tier cross-engine golden agreement (Simple is arbiter)"
```

---

## Task 8 — Walk-forward + grid optimization

**Files:** `services/analytics/__init__.py`, `services/analytics/walk_forward.py`, `services/analytics/optimization.py`, `tests/test_walk_forward.py`, `tests/test_optimization.py`.

- [ ] **Step 1: Schemas.**

```python
@dataclass(frozen=True)
class WalkForwardWindow:        is_start: str; is_end: str; oos_start: str; oos_end: str
@dataclass(frozen=True)
class WalkForwardWindowResult:  window: WalkForwardWindow; is_metrics: dict; oos_metrics: dict; best_params: dict
@dataclass(frozen=True)
class WalkForwardReport:        windows: list; aggregated_oos_equity: list; parameter_stability: dict[str, float]
```

- [ ] **Step 2: Walk-forward driver.**

```python
async def run_walk_forward(
    *, strategy_template_code: str, param_space: dict[str, list], bars: list[OHLCVBar],
    n_windows: int, is_ratio: float = 0.7, objective: str = "sharpe_ratio",
    engine_factory = VectorBTEngine,
) -> WalkForwardReport: ...
```

- [ ] **Step 3: Grid optimizer.**

```python
async def grid_search(
    *, strategy_template_code: str, param_space: dict[str, list], bars: list[OHLCVBar],
    objective: str, engine_factory,
) -> list[dict]:                # one dict per combo: {"params": ..., "metrics": ...}
```

- [ ] **Step 4: Tests.** 4-window WF with deterministic strategy → windows non-overlapping, `parameter_stability` finite. 2×2 grid → 4 combos, each `metrics` populated.

```bash
pytest tests/test_walk_forward.py tests/test_optimization.py -v
git commit -m "feat(analytics): walk-forward + grid optimization (vectorbt-backed)"
```

---

## Task 9 — Optimization REST routes + Celery

**Files:** `models/optimization_run.py`, `routers/optimization.py`, `schemas/optimization.py`, `services/tasks.py`, `main.py`, alembic `0007_create_optimization_runs.py`.

- [ ] **Step 1: Model.** `id, strategy_id, mode ("grid"|"walk_forward"), param_space (JSON), data_config (JSON), as_of_time, status, results (JSON|null), celery_task_id, created_at, completed_at, error_message`. `as_of_time` ties this run to the bitemporal store, same as `BacktestRun`.

- [ ] **Step 2: Routes.**

```
POST   /optimizations          # body: { strategy_id, mode, param_space, data_config }
GET    /optimizations          # paginated
GET    /optimizations/{id}     # status + results
DELETE /optimizations/{id}     # cancel + delete
```

`POST` always queues to Celery — these jobs are heavy by definition; no inline path.

- [ ] **Step 3: Celery task.** `@celery_app.task def run_optimization_task(run_id)` loads the run, fetches bars once with `as_of=run.as_of_time`, dispatches to `grid_search` or `run_walk_forward`, persists `results`.

- [ ] **Step 4: Integration test.** With `CELERY_TASK_ALWAYS_EAGER=True`: `POST` returns `pending` → after Celery completes → `GET` returns `completed` with results.

- [ ] **Step 5: Sync `@app/logic`** with `OptimizationMode`, `OptimizationRequest`, `OptimizationResult`.

- [ ] **Step 6: Commit.**

```bash
git commit -m "feat(api): optimization runs (grid + walk-forward) via Celery"
```

---

## Task 10 — Web optimization page + ECharts

**Files:** `apps/web/package.json`, `apps/web/src/app/(app)/optimize/[strategyId]/page.tsx`, `apps/web/src/components/charts/{Heatmap,ParallelCoordinates,WalkForwardTimeline}.tsx`, `apps/web/src/components/optimize/ParamSpaceForm.tsx`, `apps/web/e2e/optimize.spec.ts`.

- [ ] **Step 1: Install.** `pnpm --filter @app/web add echarts echarts-for-react`.

- [ ] **Step 2: ParamSpaceForm.** Rows of `{param_name, min, max, step}` → `Record<string, number[]>`. Strict Zod validation on submit.

- [ ] **Step 3: Charts.**
  - `Heatmap` — ECharts `heatmap` series for 2-param grids; cell colour = objective metric; tooltip shows full metrics.
  - `ParallelCoordinates` — ECharts `parallel` for 3+ params; one line per combination, colour by objective.
  - `WalkForwardTimeline` — stacked bars: IS metric vs OOS metric per window; highlights overfit (IS ≫ OOS).

- [ ] **Step 4: Page composition.** Header + ParamSpaceForm + Mode (Grid / Walk-forward) + Objective dropdown. Results panel polls every 2s while pending. 2 params → Heatmap, 3+ → ParallelCoordinates, walk-forward → WalkForwardTimeline.

- [ ] **Step 5: Design law.** `DM Serif Display italic` only for the page title; no shadows on standard cards; reveal animation only when results land (320 ms slide-up-fade); respect `prefers-reduced-motion`.

- [ ] **Step 6: E2E test.** Seed strategy → visit `/optimize/<id>` → fill 2 params (3 values each) → Run → wait `completed` (≤ 30 s with `CELERY_TASK_ALWAYS_EAGER`) → assert heatmap canvas present.

```bash
git commit -m "feat(web): optimization page with ECharts heatmap, parallel coords, walk-forward timeline"
```

---

## Task 11 — Web results page rebuild

**Files:** `apps/web/src/app/(app)/results/[runId]/page.tsx` and `apps/web/src/components/results/{MetricsGrid,EquityCurve,UnderwaterPlot,RollingSharpe,MonthlyReturnsHeatmap,TradeScatter,TradeTable}.tsx`, `apps/web/e2e/results.spec.ts`.

- [ ] **Step 1: Layout — 4 tabs.**
  - **Overview** — 16-metric grid (4×4, grouped headers Returns / Risk / Risk-adjusted / Trade Quality), equity curve, underwater plot (drawdown over time), rolling Sharpe (90-bar window).
  - **Trades** — trade scatter (x = exit_time, y = pnl, colour = side), sortable+filterable table, CSV export.
  - **Risk** — monthly returns heatmap (year × month), distribution histogram of trade returns, top-10 drawdowns table.
  - **Walk-Forward** — only if an `OptimizationRun` exists for this strategy.

- [ ] **Step 2: Chart library split.** Recharts for `EquityCurve`, `UnderwaterPlot`, `RollingSharpe` (line/area). ECharts for `MonthlyReturnsHeatmap`, `TradeScatter`. Both libs coexist.

- [ ] **Step 3: Reveal animation.** `motion-result-card` (320 ms slide-up-fade) on first paint when `status: completed`. Respect `prefers-reduced-motion`.

- [ ] **Step 4: E2E.** Seed completed run → visit `/results/<runId>` → assert all 4 tabs render, all charts present, trade table has rows, CSV download works.

```bash
git commit -m "feat(web): rebuild results page with 16 metrics, underwater, monthly heatmap, trade scatter"
```

---

## Task 12 — AI assistant in the editor (BYOK, swappable provider)

**Why:** E1 picked (c) — assistant, not generator. Lower risk, higher value for quant users. E2 picked (c) — BYOK; we never store keys server-side by default.

**Files:** `services/ai/{__init__,client,assistant}.py`, `routers/ai.py`, `schemas/ai.py`, `apps/web/src/components/AskAI.tsx`, `tests/test_ai_assistant.py`.

- [ ] **Step 1: LLMClient Protocol.**

```python
class LLMClient(Protocol):
    async def complete(self, *, system: str, user: str, model: str, max_tokens: int) -> str: ...
# Concrete: OpenAIClient, DeepSeekClient, AnthropicClient — all thin httpx wrappers.
```

- [ ] **Step 2: Assistant operations.** Three endpoints, each takes the user's API key in the request header (`X-LLM-Provider`, `X-LLM-Api-Key`); the server is stateless w.r.t. keys.
  - `POST /ai/explain` → body `{code, selection?}`; returns natural-language explanation.
  - `POST /ai/improve` → body `{code, instruction}`; returns proposed diff (unified diff format).
  - `POST /ai/complete` → body `{code, cursor_offset, language}`; returns inline completion suggestions.

- [ ] **Step 3: Validate every diff before returning.** `improve` runs the AST validator on the proposed code; on failure, retries up to twice with the validator error appended to the prompt; returns 422 if still invalid.

- [ ] **Step 4: Tests.** Mock `LLMClient` to return canned responses; verify retry logic; verify keys never leak into logs.

- [ ] **Step 5: Frontend `AskAI.tsx`.** Compact panel inside the Monaco editor; commands `Explain` / `Improve` / `Complete (Tab)`; key stored in `localStorage` (with a banner explaining BYOK and the privacy model).

- [ ] **Step 6: Commit.**

```bash
git commit -m "feat(ai): editor assistant with BYOK, swappable LLM provider, validator-gated diffs"
```

---

## Task 13 — Mobile MVP wiring + push notifications

**Files:** `apps/mobile/lib/{api,notifications}.ts`, `apps/mobile/app/{index,strategies,run,results}.tsx`, `apps/mobile/app/results/[runId].tsx`, `apps/api/services/{notifications,tasks}.py`.

- [ ] **Step 1: API client.** `apps/mobile/lib/api.ts` mirrors `apps/web/src/lib/api.ts`; both validate against `@app/logic` Zod schemas. No types duplicated.

- [ ] **Step 2: Five screens.**
  - `index.tsx` — dashboard: 5 most-recent runs + 3 most-recent strategies.
  - `strategies.tsx` — list + detail; code shown via `react-native-syntax-highlighter` (read-only).
  - `run.tsx` — strategy picker + data config + Run button.
  - `results.tsx` — list of runs.
  - `results/[runId].tsx` — equity curve (Victory Native), 16-metric grid, top-10 trades.

- [ ] **Step 3: Push.** `pnpm --filter @app/mobile add expo-notifications expo-device`. `lib/notifications.ts` registers device, posts token to new `POST /users/me/push-tokens`.

- [ ] **Step 4: Server-side push.** `services/notifications.py.send_push(user_id, title, body, data)` POSTs to `https://exp.host/--/api/v2/push/send`. `tasks.run_backtest_task` calls it on completion with `data={"runId": ...}` for deep-linking.

- [ ] **Step 5: Tests.** Backend `tests/test_notifications.py` mocks Expo HTTP; manual smoke: 2,000-bar backtest, observe push on a physical device.

- [ ] **Step 6: Commit.**

```bash
git commit -m "feat(mobile): wire screens to API + push notifications on Celery completion"
```

---

## Task 14 — CI gates + Phase 2 release

- [ ] **Step 1: Coverage gate (D2 = 60% floor).**

```yaml
# .github/workflows/ci.yml
- name: pytest with coverage
  run: pytest --cov=apps/api --cov-fail-under=60
- name: vitest with coverage
  run: pnpm --filter @app/logic test -- --coverage --coverage.thresholds.lines=60
```

- [ ] **Step 2: Schema-diff gate** (already added in Task 0.D; verify it runs on every PR).

- [ ] **Step 3: Verification matrix.**

```bash
cd apps/api && pytest -v
pnpm test
pnpm --filter @app/web test:e2e
pnpm lint && ruff check apps/api/
```

All green.

- [ ] **Step 4: Fresh-machine drill** (R8). On a clean VM:

```bash
git clone <repo> && cd Q && cp .env.example .env
docker compose up -d && pnpm install && pnpm dev
# Demo script (5 steps from Phase exit criteria) must succeed without extra commands.
```

Any extra step → goes back into `README.md` or `docker-compose.yml`, **not** into a "known issues" section.

- [ ] **Step 5: Demo recording.** Record the 5-step demo (≤ 3 minutes).

- [ ] **Step 6: Changelog.** Extend `CHANGELOG.md` with `## v0.2.0 — 2026-06-21` enumerating every shipped Task.

- [ ] **Step 7: Tag.**

```bash
git tag -a v0.2.0 -m "Phase 2: Real Engine & Quant Depth"
# Per CLAUDE.md: do NOT push without explicit confirmation.
```

- [ ] **Step 8: Write Phase 3 plan.** Create `docs/superpowers/plans/2026-06-22-phase-3-realism-tier-2-and-portfolio.md` following this same Task/Step format, seeded from the Phase 3 sketch in the roadmap.

---

## Done — Phase 2 Complete

When this checklist is fully checked:

- The data layer is **point-in-time correct** (bitemporal store, every backtest bound to `as_of_time`).
- The strategy execution path is **sandboxed** (subprocess + `setrlimit` + validator).
- The backtest engine is **trustworthy** (commission / slippage / fill).
- The metrics are **dense** (16+ scalars + monthly heatmap + trade scatter).
- There are **three engines** (Simple, VectorBT, Backtrader) with three-tier cross-engine golden agreement; SimpleEngine is the arbiter.
- The system has its **first quant-grade headline feature** (walk-forward + grid optimization).
- It has an **AI assistant in the editor** (BYOK, swappable provider, validator-gated diffs).
- It is **usable on mobile** with **push notifications**.
- It has **CI gates** (≥ 60% coverage, schema-diff, lint, typecheck, E2E).
- It is **reproducible from a fresh clone** in under 3 minutes.

Proceed to Phase 3 (Realism Tier 2 + multi-asset portfolio + corporate actions + survivorship-bias correction).
