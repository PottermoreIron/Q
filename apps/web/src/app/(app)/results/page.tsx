"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  backtests as backteststApi,
  type BacktestRun,
  type Trade,
} from "@/lib/api";
import { ErrorBanner } from "@/components/ErrorBanner";
import { formatApiError } from "@/lib/format-api-error";

// ── Palette for multi-run comparison (non-accent, value-driven) ───────────────
const SERIES_COLORS = [
  "#37352F", // ink
  "#16A34A", // positive
  "#D97706", // warning
  "#1a6fa8", // blue
  "#9B9A97", // muted
  "#DC2626", // negative
];

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—";
  return n.toFixed(decimals);
}
function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return (n * 100).toFixed(2) + "%";
}
function fmtCurrency(n: number | null | undefined): string {
  if (n == null) return "—";
  return (
    "$" +
    n.toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })
  );
}

function formatAxisDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      year: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ── CSV export ────────────────────────────────────────────────────────────────

function exportEquityCsv(run: BacktestRun) {
  if (!run.equityCurve) return;
  const rows = [
    ["timestamp", "equity"],
    ...run.equityCurve.map(([t, v]) => [t, v.toFixed(2)]),
  ];
  const csv = rows.map((r) => r.join(",")).join("\n");
  download(`equity_${run.id.slice(0, 8)}.csv`, csv);
}

function exportTradesCsv(run: BacktestRun) {
  if (!run.trades?.length) return;
  const headers = ["entryPrice", "exitPrice", "pnl", "side"];
  const rows = [
    headers,
    ...run.trades.map((t) => [
      t.entryPrice,
      t.exitPrice,
      t.pnl.toFixed(2),
      t.side,
    ]),
  ];
  const csv = rows.map((r) => r.join(",")).join("\n");
  download(`trades_${run.id.slice(0, 8)}.csv`, csv);
}

function download(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ResultsPage() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const loadRuns = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    backteststApi
      .list()
      .then((data) => setRuns(data.filter((r) => r.status === "completed")))
      .catch((err: unknown) => {
        setLoadError(formatApiError(err, "Failed to load completed runs."));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const toggle = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selected = runs.filter((r) => selectedIds.has(r.id));

  return (
    <div className="flex gap-8 min-h-0">
      {/* ── Left: run list ───────────────────────────────────────────────── */}
      <div className="w-72 flex-shrink-0">
        <div className="mb-6">
          <h1 className="font-serif italic text-display text-ink mb-1">
            Results
          </h1>
          <p className="text-body text-muted">
            Select one or more completed runs to compare.
          </p>
        </div>

        {loading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-16 bg-border rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : loadError ? (
          <ErrorBanner message={loadError} onRetry={loadRuns} />
        ) : runs.length === 0 ? (
          <div className="py-12 text-center">
            <p className="font-serif italic text-title text-muted">
              No completed runs yet.
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {runs.map((r, i) => {
              const active = selectedIds.has(r.id);
              const colorIdx = [...selectedIds].indexOf(r.id);
              const dotColor =
                active && colorIdx >= 0
                  ? SERIES_COLORS[colorIdx % SERIES_COLORS.length]
                  : undefined;
              return (
                <button
                  key={r.id}
                  onClick={() => toggle(r.id)}
                  className={`w-full text-left px-3 py-3 rounded-md border transition-colors duration-[80ms] ${
                    active
                      ? "border-ink bg-surface"
                      : "border-transparent hover:bg-surface"
                  }`}
                  style={{ animationDelay: `${i * 30}ms` }}
                >
                  <div className="flex items-center gap-2">
                    {dotColor && (
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: dotColor }}
                      />
                    )}
                    <span className="text-small text-ink font-medium truncate">
                      {r.strategyName}
                    </span>
                  </div>
                  <p className="text-small text-muted mt-0.5 pl-4">
                    {r.dataConfig.symbol} · {r.dataConfig.timeframe} ·{" "}
                    {fmtCurrency(r.metrics?.finalValue)}
                  </p>
                  <p className="text-small text-muted pl-4">
                    Sharpe {fmt(r.metrics?.sharpeRatio)} · DD{" "}
                    {fmtPct(r.metrics?.maxDrawdown)}
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Right: detail / comparison ───────────────────────────────────── */}
      <div className="flex-1 min-w-0">
        {selected.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <p className="font-serif italic text-title text-muted">
              Select a run from the list.
            </p>
          </div>
        ) : selected.length === 1 ? (
          <SingleRunView run={selected[0]} />
        ) : (
          <ComparisonView runs={selected} />
        )}
      </div>
    </div>
  );
}

// ── Single run view ───────────────────────────────────────────────────────────

function SingleRunView({ run }: { run: BacktestRun }) {
  const m = run.metrics;
  const [tab, setTab] = useState<"chart" | "trades">("chart");

  return (
    <div className="space-y-6 animate-slide-up-fade">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-serif italic text-title text-ink">
            {run.strategyName}
          </h2>
          <p className="text-small text-muted mt-0.5">
            {run.dataConfig.symbol} · {run.dataConfig.assetClass} ·{" "}
            {run.dataConfig.timeframe} · {run.dataConfig.startDate} →{" "}
            {run.dataConfig.endDate}
          </p>
        </div>
        <div className="flex gap-2">
          {run.equityCurve && (
            <button
              onClick={() => exportEquityCsv(run)}
              className="px-3 py-1.5 border border-border rounded-md text-small text-muted hover:text-body transition-colors duration-[80ms]"
            >
              Export equity
            </button>
          )}
          {run.trades?.length ? (
            <button
              onClick={() => exportTradesCsv(run)}
              className="px-3 py-1.5 border border-border rounded-md text-small text-muted hover:text-body transition-colors duration-[80ms]"
            >
              Export trades
            </button>
          ) : null}
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Final value" value={fmtCurrency(m?.finalValue)} />
        <MetricCard label="CAGR" value={fmtPct(m?.cagr)} />
        <MetricCard label="Sharpe" value={fmt(m?.sharpeRatio)} />
        <MetricCard label="Sortino" value={fmt(m?.sortinoRatio)} />
        <MetricCard
          label="Max drawdown"
          value={fmtPct(m?.maxDrawdown)}
          negative={!!m?.maxDrawdown && m.maxDrawdown < 0}
        />
        <MetricCard label="Win rate" value={fmtPct(m?.winRate)} />
        <MetricCard label="Profit factor" value={fmt(m?.profitFactor)} />
        <MetricCard
          label="Total trades"
          value={String(m?.totalTrades ?? "—")}
        />
      </div>

      {/* Tab bar */}
      <div className="flex gap-4 border-b border-border">
        {(["chart", "trades"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-body capitalize border-b-2 transition-colors duration-[80ms] ${
              tab === t
                ? "border-ink text-ink"
                : "border-transparent text-muted hover:text-body"
            }`}
          >
            {t === "trades"
              ? `Trades (${run.trades?.length ?? 0})`
              : "Equity curve"}
          </button>
        ))}
      </div>

      {tab === "chart" && <EquityCurveChart runs={[run]} />}
      {tab === "trades" && <TradeLog trades={run.trades ?? []} />}
    </div>
  );
}

// ── Multi-run comparison view ─────────────────────────────────────────────────

function ComparisonView({ runs }: { runs: BacktestRun[] }) {
  return (
    <div className="space-y-6 animate-slide-up-fade">
      <div>
        <h2 className="font-serif italic text-title text-ink">
          Comparing {runs.length} runs
        </h2>
        <p className="text-small text-muted mt-0.5">Equity curves overlaid.</p>
      </div>

      <EquityCurveChart runs={runs} />

      {/* Comparison table */}
      <div className="overflow-x-auto">
        <table className="w-full text-small">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 text-muted font-medium">
                Strategy
              </th>
              <th className="text-right py-2 px-4 text-muted font-medium">
                Final value
              </th>
              <th className="text-right py-2 px-4 text-muted font-medium">
                CAGR
              </th>
              <th className="text-right py-2 px-4 text-muted font-medium">
                Sharpe
              </th>
              <th className="text-right py-2 px-4 text-muted font-medium">
                Max DD
              </th>
              <th className="text-right py-2 px-4 text-muted font-medium">
                Win rate
              </th>
              <th className="text-right py-2 pl-4 text-muted font-medium">
                Trades
              </th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r, i) => {
              const m = r.metrics;
              const color = SERIES_COLORS[i % SERIES_COLORS.length];
              return (
                <tr key={r.id} className="border-b border-border last:border-0">
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: color }}
                      />
                      <span className="text-ink font-medium">
                        {r.strategyName}
                      </span>
                      <span className="text-muted">{r.dataConfig.symbol}</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-right text-ink">
                    {fmtCurrency(m?.finalValue)}
                  </td>
                  <td className="py-2.5 px-4 text-right text-ink">
                    {fmtPct(m?.cagr)}
                  </td>
                  <td className="py-2.5 px-4 text-right text-ink">
                    {fmt(m?.sharpeRatio)}
                  </td>
                  <td
                    className={`py-2.5 px-4 text-right ${m?.maxDrawdown != null && m.maxDrawdown < 0 ? "text-negative" : "text-ink"}`}
                  >
                    {fmtPct(m?.maxDrawdown)}
                  </td>
                  <td className="py-2.5 px-4 text-right text-ink">
                    {fmtPct(m?.winRate)}
                  </td>
                  <td className="py-2.5 pl-4 text-right text-ink">
                    {m?.totalTrades ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Equity curve chart ────────────────────────────────────────────────────────

function EquityCurveChart({ runs }: { runs: BacktestRun[] }) {
  const isMulti = runs.length > 1;

  if (isMulti) {
    // Merge all curves into one dataset keyed by timestamp
    const allTimestamps = new Set<string>();
    const seriesMap: Record<string, Record<string, number>> = {};

    runs.forEach((r, i) => {
      const key = `${r.strategyName} (${r.dataConfig.symbol})`;
      seriesMap[key] = {};
      (r.equityCurve ?? []).forEach(([t, v]) => {
        allTimestamps.add(t);
        seriesMap[key][t] = v;
      });
    });

    const timestamps = [...allTimestamps].sort();
    const data = timestamps.map((t) => {
      const point: Record<string, string | number> = { t };
      Object.entries(seriesMap).forEach(([key, values]) => {
        if (values[t] !== undefined) point[key] = values[t];
      });
      return point;
    });

    const seriesKeys = Object.keys(seriesMap);

    return (
      <div className="bg-surface border border-border rounded-lg p-4">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart
            data={data}
            margin={{ top: 4, right: 16, bottom: 4, left: 16 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" />
            <XAxis
              dataKey="t"
              tickFormatter={formatAxisDate}
              tick={{ fontSize: 11, fill: "#9B9A97" }}
              tickLine={false}
              axisLine={{ stroke: "#E9E9E7" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={(v: number) => "$" + (v / 1000).toFixed(0) + "k"}
              tick={{ fontSize: 11, fill: "#9B9A97" }}
              tickLine={false}
              axisLine={false}
              width={52}
            />
            <Tooltip
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(v: any, name: any) => [
                fmtCurrency(v as number),
                name as string,
              ]}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              labelFormatter={(iso: any) => formatAxisDate(String(iso))}
              contentStyle={{
                border: "1px solid #E9E9E7",
                borderRadius: 6,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: "#9B9A97" }} />
            {seriesKeys.map((key, i) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Single run — AreaChart with gradient fill
  const run = runs[0];
  const data = (run.equityCurve ?? []).map(([t, v]) => ({ t, v }));

  if (data.length === 0) {
    return (
      <div className="bg-surface border border-border rounded-lg p-6 text-center">
        <p className="text-small text-muted">No equity curve data.</p>
      </div>
    );
  }

  const gradId = "eq-grad";

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart
          data={data}
          margin={{ top: 4, right: 16, bottom: 4, left: 16 }}
        >
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#37352F" stopOpacity={0.08} />
              <stop offset="95%" stopColor="#37352F" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" />
          <XAxis
            dataKey="t"
            tickFormatter={formatAxisDate}
            tick={{ fontSize: 11, fill: "#9B9A97" }}
            tickLine={false}
            axisLine={{ stroke: "#E9E9E7" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(v: number) => "$" + (v / 1000).toFixed(0) + "k"}
            tick={{ fontSize: 11, fill: "#9B9A97" }}
            tickLine={false}
            axisLine={false}
            width={52}
          />
          <Tooltip
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(v: any) => [fmtCurrency(v as number), "Equity"]}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            labelFormatter={(iso: any) => formatAxisDate(String(iso))}
            contentStyle={{
              border: "1px solid #E9E9E7",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Area
            type="monotone"
            dataKey="v"
            stroke="#37352F"
            strokeWidth={1.5}
            fill={`url(#${gradId})`}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Trade log table ───────────────────────────────────────────────────────────

function TradeLog({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) {
    return (
      <div className="py-8 text-center">
        <p className="text-small text-muted">No trades in this run.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-small">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-2 pr-4 text-muted font-medium">#</th>
            <th className="text-right py-2 px-4 text-muted font-medium">
              Entry
            </th>
            <th className="text-right py-2 px-4 text-muted font-medium">
              Exit
            </th>
            <th className="text-right py-2 px-4 text-muted font-medium">
              P&amp;L
            </th>
            <th className="text-right py-2 pl-4 text-muted font-medium">
              Return
            </th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t, i) => {
            const ret = (t.exitPrice - t.entryPrice) / t.entryPrice;
            const win = t.pnl > 0;
            return (
              <tr
                key={i}
                className="border-b border-border last:border-0 hover:bg-[#fafaf9] transition-colors duration-[80ms]"
              >
                <td className="py-2 pr-4 text-muted">{i + 1}</td>
                <td className="py-2 px-4 text-right text-ink">
                  ${t.entryPrice.toFixed(2)}
                </td>
                <td className="py-2 px-4 text-right text-ink">
                  ${t.exitPrice.toFixed(2)}
                </td>
                <td
                  className={`py-2 px-4 text-right font-medium ${win ? "text-positive" : "text-negative"}`}
                >
                  {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                </td>
                <td
                  className={`py-2 pl-4 text-right ${win ? "text-positive" : "text-negative"}`}
                >
                  {(ret * 100).toFixed(2)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Metric card ───────────────────────────────────────────────────────────────

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
      <p
        className={`text-title font-medium ${negative ? "text-negative" : "text-ink"}`}
      >
        {value}
      </p>
    </div>
  );
}
