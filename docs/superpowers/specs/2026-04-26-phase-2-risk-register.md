# Phase 2 — Risk Register

> Companion to `2026-04-26-phase-2-real-engine-and-quant-depth.md`.
> Each risk has an **owner** (who decides), a **trigger** (the observable that escalates it), and a **mitigation** (the pre-agreed response).
> Reviewed at the end of every week's review checkpoint.

---

## R1 · Bitemporal data store ships late

- **Owner:** human (architect call).
- **Trigger:** end of Week 1 review, Task 0.A still in progress.
- **Why it's catastrophic:** every downstream Task (1-13) assumes point-in-time replay. If Task 0 slips into Week 2, Tasks 4-7 (engines + golden + walk-forward) will be built on the old Redis-only cache and need to be redone.
- **Mitigation:**
  1. Hard freeze: no Task 1+ work begins until Task 0.A migration is merged and `as_of_time` is wired into `BacktestRun`.
  2. If still red at Week 1 EOD, cut Task 12 (mobile) and Task 11 (AI assistant) from Phase 2 immediately to recover budget — do **not** cut Task 0.

---

## R2 · VectorBT and Backtrader disagree beyond Tier-2 tolerance (2%)

- **Owner:** human (numerical judgment).
- **Trigger:** Task 7 cross-engine golden test fails on `sharpe_ratio` or `cagr` after the third tuning attempt on either adapter.
- **Why it matters:** the core promise is "trustworthy backtest". Two engines that disagree by >2% on the same SMA-crossover means at least one is wrong, and we don't yet know which.
- **Mitigation:**
  1. SimpleEngine is the **arbiter** — it is small enough to step through by hand. If SimpleEngine and VectorBT agree, Backtrader is wrong; if SimpleEngine and Backtrader agree, VectorBT is wrong.
  2. Document the gap in `docs/engines/known-discrepancies.md` with a minimal repro before relaxing the tolerance. Never silently widen the threshold.
  3. Acceptable fallback: ship Phase 2 with VectorBT marked **stable** and Backtrader marked **experimental** (registry hint still works, but cross-engine golden only enforces Simple↔VectorBT). Backtrader stability moves to Phase 3.

---

## R3 · Subprocess sandbox is too slow for inline path

- **Owner:** agent (perf measurement) → human (decision).
- **Trigger:** sandbox cold-start adds >300ms to a 500-bar inline backtest, breaking the "<5s end-to-end" demo criterion.
- **Why it matters:** every backtest pays the sandbox cost. If it's heavy, users will feel it on every keystroke during strategy iteration.
- **Mitigation (in order of preference):**
  1. Pre-fork a sandbox worker pool (one warm subprocess per CPU core) with `multiprocessing.get_context("forkserver")`. Reduces cold-start from ~150ms (CPython spawn) to ~5ms.
  2. If still too slow: keep sandbox mandatory only for Celery jobs; inline path uses validator + `_SAFE_BUILTINS` (current behavior) **and** the API response carries `sandbox: "in_process" | "subprocess"` so users can see what ran.
  3. Never bypass the sandbox silently.

---

## R4 · Strategy contract divergence between block_compiler and engines

- **Owner:** agent.
- **Trigger:** Task 4 or 5 finds that `block_compiler` output doesn't compose cleanly with the engine adapter (e.g., `stop_loss_pct` is set as a free variable, not in the return dict).
- **Why it matters:** if the block-compiled code only runs on SimpleEngine, the value of having three engines collapses.
- **Mitigation:**
  1. Lock the contract in `apps/api/services/engines/strategy_contract.py` (Task 0.B exit criteria). Both `block_compiler.py` and every engine adapter read from this single module.
  2. Add a contract test (`tests/test_strategy_contract.py`) that for each block recipe, runs it on **all three engines** and asserts the result shape matches.

---

## R5 · Bitemporal store grows unboundedly

- **Owner:** human (capacity planning).
- **Trigger:** `ohlcv_bars` row count crosses 50M, or a single `(symbol, timeframe)` query takes >500ms.
- **Why it matters:** correctness comes from append-only history, but unbounded growth eventually hurts queries.
- **Mitigation:**
  1. Phase 2 only enforces correctness, not size. No partitioning yet.
  2. Phase 3 will add monthly partitioning on `ts` and a `compress_history(symbol, before_date)` job that keeps only the latest `effective_from` for each `(symbol, ts)` older than 1 year.
  3. Document this in the Phase 3 sketch — do not preempt it in Phase 2.

---

## R6 · LLM provider drift breaks the AI assistant

- **Owner:** human (provider strategy).
- **Trigger:** any `tests/test_ai_assistant.py` integration test fails after a provider deprecates a model or changes response shape.
- **Why it matters:** users bring their own keys (BYOK), but the prompt template and response parser still live in our code.
- **Mitigation:**
  1. The assistant calls a thin `LLMClient` Protocol — providers (`OpenAIClient`, `DeepSeekClient`, `AnthropicClient`) are swappable via a single `provider=` param.
  2. Integration tests use recorded fixtures (VCR-style); only one nightly job hits a real provider to detect drift.
  3. AI assistant is a **secondary** feature in Phase 2 — its breakage never blocks the engine/data work or the release tag.

---

## R7 · Real-PostgreSQL test suite slows CI past 10 minutes

- **Owner:** agent.
- **Trigger:** `pnpm test` + `pytest` total CI time exceeds 10 minutes on a clean runner.
- **Why it matters:** slow CI erodes the test-driven discipline.
- **Mitigation:**
  1. Use `pytest-xdist` to parallelize integration tests across cores.
  2. Reuse a single PostgreSQL container per test session via `pytest` fixture with `scope="session"`; truncate tables between tests instead of dropping schemas.
  3. Hard cap: if the suite still exceeds 10 minutes, gate the slowest 20% of integration tests behind `pytest -m slow` and run them only on `main` and `release/*` branches.

---

## R8 · Showcase demo is not reproducible on a fresh clone

- **Owner:** human (release gate).
- **Trigger:** Task 14 (release) — running the 4-step demo from a fresh `git clone` + `docker compose up -d` + `pnpm install` requires more than the documented commands.
- **Why it matters:** an open-source project that doesn't run on day 1 is dead on arrival.
- **Mitigation:**
  1. Task 14 includes a "fresh-machine drill" performed by the human, not the agent.
  2. Any extra command the human had to type goes back into `README.md` or `docker-compose.yml` defaults — never into a "known issues" section.
  3. The `v0.2.0` tag does not ship until the drill passes.

---

## Review cadence

- **Weekly checkpoint** (Friday): walk this register, mark each row as `green | yellow | red`, escalate any `red` to a same-day decision.
- **Phase exit:** every row must be either `green` or have a written follow-up issue carried into Phase 3.
