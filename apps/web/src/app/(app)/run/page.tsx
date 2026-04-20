"use client";

import { useEffect, useRef, useState } from "react";
import {
  strategies as strategiesApi,
  backtests as backteststApi,
  type Strategy,
  type BacktestRun,
  type DataConfig,
  type AssetClass,
  type Timeframe,
  type DataSource,
} from "@/lib/api";
import { Select } from "@/components/Select";
import { SegmentedControl } from "@/components/SegmentedControl";

const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: "1m",  label: "1 min"   },
  { value: "5m",  label: "5 min"   },
  { value: "15m", label: "15 min"  },
  { value: "30m", label: "30 min"  },
  { value: "1h",  label: "1 hour"  },
  { value: "4h",  label: "4 hours" },
  { value: "1d",  label: "1 day"   },
  { value: "1w",  label: "1 week"  },
  { value: "1M",  label: "1 month" },
];

const ASSET_CLASSES: { value: AssetClass; label: string }[] = [
  { value: "stock",   label: "Stock"   },
  { value: "crypto",  label: "Crypto"  },
  { value: "forex",   label: "Forex"   },
  { value: "futures", label: "Futures" },
];

function fmt(n: number | null | undefined, decimals = 2, suffix = ""): string {
  if (n == null) return "—";
  return n.toFixed(decimals) + suffix;
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return (n * 100).toFixed(2) + "%";
}

function statusPill(status: BacktestRun["status"]) {
  const map: Record<BacktestRun["status"], string> = {
    pending:   "bg-[#f0f0ef] text-[#6f6f6e]",
    running:   "bg-[#e8f4fd] text-[#1a6fa8]",
    completed: "bg-[#edf7ed] text-[#2d7a2d]",
    failed:    "bg-[#fdecea] text-[#c0392b]",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-small font-medium ${map[status]}`}>
      {status}
    </span>
  );
}

export default function RunPage() {
  const [strategyList, setStrategyList] = useState<Strategy[]>([]);
  const [runs, setRuns]                 = useState<BacktestRun[]>([]);
  const [loadingStrategies, setLoadingStrategies] = useState(true);

  // form state
  const [strategyId, setStrategyId] = useState("");
  const [symbol,     setSymbol]     = useState("AAPL");
  const [assetClass, setAssetClass] = useState<AssetClass>("stock");
  const [timeframe,  setTimeframe]  = useState<Timeframe>("1d");
  const [startDate,  setStartDate]  = useState("2023-01-01");
  const [endDate,    setEndDate]    = useState("2023-12-31");

  // submission state
  const [submitting, setSubmitting] = useState(false);
  const [runError,   setRunError]   = useState<string | null>(null);

  // selected run for detail view
  const [selectedRun, setSelectedRun] = useState<BacktestRun | null>(null);

  // polling
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    strategiesApi.list().then(setStrategyList).finally(() => setLoadingStrategies(false));
    backteststApi.list().then(setRuns);
  }, []);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function startPolling(runId: string) {
    stopPolling();
    pollRef.current = setInterval(async () => {
      const updated = await backteststApi.get(runId);
      setRuns((prev) => prev.map((r) => (r.id === runId ? updated : r)));
      setSelectedRun((prev) => (prev?.id === runId ? updated : prev));
      if (updated.status === "completed" || updated.status === "failed") {
        stopPolling();
      }
    }, 1500);
  }

  useEffect(() => () => stopPolling(), []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!strategyId) return;
    setRunError(null);
    setSubmitting(true);
    try {
      const cfg: DataConfig = {
        source: assetClass === "crypto" ? "binance" : "yahoo" as DataSource,
        symbol,
        asset_class: assetClass,
        timeframe,
        start_date: startDate,
        end_date:   endDate,
      };
      const run = await backteststApi.create({ strategy_id: strategyId, data_config: cfg });
      setRuns((prev) => [run, ...prev]);
      setSelectedRun(run);
      if (run.status === "pending" || run.status === "running") {
        startPolling(run.id);
      }
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(runId: string) {
    await backteststApi.delete(runId);
    setRuns((prev) => prev.filter((r) => r.id !== runId));
    if (selectedRun?.id === runId) setSelectedRun(null);
  }

  const selectedStrategy = strategyList.find((s) => s.id === strategyId);

  return (
    <div className="flex gap-8 h-full min-h-0">
      {/* ── Left column: form + run list ───────────────────────────────────── */}
      <div className="w-80 flex-shrink-0 flex flex-col gap-6">
        <div>
          <h1 className="font-serif italic text-display text-ink mb-1">Run Backtest</h1>
          <p className="text-body text-muted">Configure data and launch a run.</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Strategy */}
          <div>
            <label className="block text-small text-muted mb-1">Strategy</label>
            {loadingStrategies ? (
              <div className="h-9 bg-border rounded animate-pulse" />
            ) : (
              <Select
                options={strategyList.map((s) => ({ value: s.id, label: s.name }))}
                value={strategyId}
                onChange={setStrategyId}
                placeholder="Select a strategy…"
              />
            )}
          </div>

          {/* Symbol */}
          <div>
            <label className="block text-small text-muted mb-1">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => {
                const v = e.target.value.toUpperCase();
                setSymbol(v);
                if (v.includes("/")) setAssetClass("crypto");
              }}
              placeholder="AAPL"
              required
              className="w-full px-3 py-2 bg-surface border border-border rounded-md text-small text-[#191919] placeholder:text-muted focus:outline-none focus:border-[#37352F] transition-colors duration-[80ms]"
            />
          </div>

          {/* Asset class */}
          <div>
            <label className="block text-small text-muted mb-1">Asset class</label>
            <SegmentedControl
              options={ASSET_CLASSES}
              value={assetClass}
              onChange={setAssetClass}
            />
          </div>

          {/* Timeframe */}
          <div>
            <label className="block text-small text-muted mb-1">Timeframe</label>
            <SegmentedControl
              options={TIMEFRAMES}
              value={timeframe}
              onChange={setTimeframe}
            />
          </div>

          {/* Date range */}
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-small text-muted mb-1">From</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="w-full px-3 py-2 bg-surface border border-border rounded-md text-small text-[#191919] focus:outline-none focus:border-[#37352F] transition-colors duration-[80ms] [color-scheme:light] [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:cursor-pointer"
              />
            </div>
            <div className="flex-1">
              <label className="block text-small text-muted mb-1">To</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className="w-full px-3 py-2 bg-surface border border-border rounded-md text-small text-[#191919] focus:outline-none focus:border-[#37352F] transition-colors duration-[80ms] [color-scheme:light] [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:cursor-pointer"
              />
            </div>
          </div>

          {runError && (
            <p className="text-small text-negative">{runError}</p>
          )}

          <button
            type="submit"
            disabled={submitting || !strategyId}
            className="w-full py-2 bg-ink text-white text-body font-medium rounded-md disabled:opacity-40 active:scale-[0.97] transition-transform duration-[80ms]"
          >
            {submitting ? "Launching…" : "Run Backtest"}
          </button>
        </form>

        {/* Run list */}
        {runs.length > 0 && (
          <div>
            <p className="text-small text-muted mb-2">Recent runs</p>
            <div className="space-y-1">
              {runs.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelectedRun(r)}
                  className={`w-full text-left px-3 py-2 rounded-md border transition-colors duration-[80ms] ${
                    selectedRun?.id === r.id
                      ? "border-ink bg-surface"
                      : "border-transparent hover:bg-surface"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-small text-ink font-medium truncate max-w-[140px]">
                      {r.strategy_name}
                    </span>
                    {statusPill(r.status)}
                  </div>
                  <p className="text-small text-muted mt-0.5">
                    {r.data_config.symbol} · {r.data_config.timeframe}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Right column: run detail ────────────────────────────────────────── */}
      <div className="flex-1 min-w-0">
        {!selectedRun ? (
          <div className="h-full flex items-center justify-center">
            <p className="font-serif italic text-title text-muted">
              Select or launch a run to see results.
            </p>
          </div>
        ) : (
          <RunDetail run={selectedRun} onDelete={handleDelete} />
        )}
      </div>
    </div>
  );
}


// ── Run detail panel ──────────────────────────────────────────────────────────

function RunDetail({
  run,
  onDelete,
}: {
  run: BacktestRun;
  onDelete: (id: string) => void;
}) {
  const m = run.metrics;
  const cfg = run.data_config;

  return (
    <div className="space-y-6 animate-slide-up-fade">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-serif italic text-title text-ink">{run.strategy_name}</h2>
          <p className="text-small text-muted mt-0.5">
            {cfg.symbol} · {cfg.asset_class} · {cfg.timeframe} · {cfg.start_date} → {cfg.end_date}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {statusPill(run.status)}
          <button
            onClick={() => onDelete(run.id)}
            className="text-small text-muted hover:text-negative transition-colors duration-[80ms]"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Pending/running */}
      {(run.status === "pending" || run.status === "running") && (
        <div className="py-12 flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-ink border-t-transparent rounded-full animate-spin" />
          <p className="text-body text-muted">
            {run.status === "pending" ? "Queued…" : "Running…"}
          </p>
        </div>
      )}

      {/* Failed */}
      {run.status === "failed" && (
        <div className="bg-[#fdecea] border border-[#f5c6c2] rounded-lg px-5 py-4">
          <p className="text-body text-negative font-medium mb-1">Run failed</p>
          <p className="text-small text-negative font-mono whitespace-pre-wrap">
            {run.error_message ?? "No error details."}
          </p>
        </div>
      )}

      {/* Completed */}
      {run.status === "completed" && m && (
        <>
          {/* Metrics grid */}
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Final value"   value={`$${fmt(m.final_value, 0)}`} />
            <MetricCard label="Sharpe ratio"  value={fmt(m.sharpe_ratio)}  />
            <MetricCard label="Sortino ratio" value={fmt(m.sortino_ratio)} />
            <MetricCard label="CAGR"          value={fmtPct(m.cagr)}       />
            <MetricCard label="Max drawdown"  value={fmtPct(m.max_drawdown)} negative={m.max_drawdown != null && m.max_drawdown < 0} />
            <MetricCard label="Win rate"      value={fmtPct(m.win_rate)}   />
            <MetricCard label="Profit factor" value={fmt(m.profit_factor)} />
            <MetricCard label="Total trades"  value={String(m.total_trades ?? "—")} />
          </div>

          {/* Log */}
          {run.log_output && (
            <div>
              <p className="text-small text-muted mb-1">Log</p>
              <pre className="text-small font-mono text-ink bg-surface border border-border rounded-lg px-4 py-3 whitespace-pre-wrap">
                {run.log_output}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  negative = false,
}: {
  label: string;
  value: string;
  negative?: boolean;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg px-4 py-3">
      <p className="text-small text-muted mb-1">{label}</p>
      <p className={`text-title font-medium ${negative ? "text-negative" : "text-ink"}`}>
        {value}
      </p>
    </div>
  );
}
