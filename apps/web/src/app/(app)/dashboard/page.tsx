"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  strategies as strategiesApi,
  backtests as backteststApi,
  type Strategy,
  type BacktestRun,
} from "@/lib/api";

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
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function DashboardPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [runs, setRuns]             = useState<BacktestRun[]>([]);
  const [loading, setLoading]       = useState(true);

  useEffect(() => {
    Promise.all([strategiesApi.list(), backteststApi.list()])
      .then(([s, r]) => {
        setStrategies(s);
        setRuns(r);
      })
      .finally(() => setLoading(false));
  }, []);

  const completedRuns = runs.filter((r) => r.status === "completed");
  const recentRuns    = runs.slice(0, 5);

  // Best run by Sharpe
  const bestRun = completedRuns.reduce<BacktestRun | null>((best, r) => {
    if (!r.metrics?.sharpe_ratio) return best;
    if (!best?.metrics?.sharpe_ratio) return r;
    return r.metrics.sharpe_ratio > best.metrics.sharpe_ratio ? r : best;
  }, null);

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="font-serif italic text-display text-ink mb-1">Dashboard</h1>
          <p className="text-body text-muted">Overview of your strategies and runs.</p>
        </div>
        <Link
          href="/strategies/new"
          className="px-4 py-2 bg-ink text-white text-body font-medium rounded-md active:scale-[0.97] transition-transform duration-[80ms]"
        >
          New Strategy
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-border rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          {/* Stats row */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              label="Strategies"
              value={String(strategies.length)}
              sub="total saved"
              href="/strategies"
            />
            <StatCard
              label="Completed runs"
              value={String(completedRuns.length)}
              sub={`${runs.length} total`}
              href="/results"
            />
            <StatCard
              label="Best Sharpe"
              value={fmt(bestRun?.metrics?.sharpe_ratio)}
              sub={bestRun ? `${bestRun.strategy_name} · ${bestRun.data_config.symbol}` : "no runs yet"}
              href="/results"
            />
          </div>

          {/* Recent runs */}
          <div>
            <div className="flex items-baseline justify-between mb-4">
              <h2 className="font-serif italic text-title text-ink">Recent runs</h2>
              <Link href="/results" className="text-small text-muted hover:text-body transition-colors duration-[80ms]">
                View all →
              </Link>
            </div>

            {recentRuns.length === 0 ? (
              <div className="py-10 text-center border border-border rounded-lg">
                <p className="font-serif italic text-title text-muted mb-3">No runs yet.</p>
                <Link
                  href="/run"
                  className="px-4 py-2 bg-ink text-white text-body font-medium rounded-md"
                >
                  Run a backtest
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {recentRuns.map((r, i) => (
                  <RunRow key={r.id} run={r} idx={i} />
                ))}
              </div>
            )}
          </div>

          {/* Strategies */}
          <div>
            <div className="flex items-baseline justify-between mb-4">
              <h2 className="font-serif italic text-title text-ink">Strategies</h2>
              <Link href="/strategies" className="text-small text-muted hover:text-body transition-colors duration-[80ms]">
                View all →
              </Link>
            </div>

            {strategies.length === 0 ? (
              <div className="py-10 text-center border border-border rounded-lg">
                <p className="font-serif italic text-title text-muted mb-3">No strategies yet.</p>
                <Link
                  href="/strategies/new"
                  className="px-4 py-2 bg-ink text-white text-body font-medium rounded-md"
                >
                  Create your first strategy
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {strategies.slice(0, 5).map((s, i) => (
                  <div
                    key={s.id}
                    className="bg-surface border border-border rounded-lg px-5 py-3 flex items-center justify-between animate-slide-up-fade"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <div>
                      <Link
                        href={`/strategies/${s.id}`}
                        className="font-serif italic text-title text-ink hover:opacity-70 transition-opacity duration-[80ms]"
                      >
                        {s.name}
                      </Link>
                      {s.description && (
                        <p className="text-small text-muted mt-0.5">{s.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-small text-muted">
                        {s.blocks.length} block{s.blocks.length !== 1 ? "s" : ""}
                      </span>
                      <Link
                        href={`/run?strategy_id=${s.id}`}
                        className="text-small text-muted hover:text-body transition-colors duration-[80ms]"
                      >
                        Run →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
  href,
}: {
  label: string;
  value: string;
  sub: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="bg-surface border border-border rounded-lg px-5 py-4 block hover:border-ink/30 transition-colors duration-[80ms]"
    >
      <p className="text-small text-muted mb-1">{label}</p>
      <p className="text-display font-medium text-ink">{value}</p>
      <p className="text-small text-muted mt-1 truncate">{sub}</p>
    </Link>
  );
}

function RunRow({ run, idx }: { run: BacktestRun; idx: number }) {
  const m = run.metrics;
  const statusColor: Record<BacktestRun["status"], string> = {
    pending:   "text-muted",
    running:   "text-[#1a6fa8]",
    completed: "text-positive",
    failed:    "text-negative",
  };

  return (
    <div
      className="bg-surface border border-border rounded-lg px-5 py-3 flex items-center justify-between animate-slide-up-fade"
      style={{ animationDelay: `${idx * 40}ms` }}
    >
      <div>
        <p className="text-body text-ink font-medium">{run.strategy_name}</p>
        <p className="text-small text-muted mt-0.5">
          {run.data_config.symbol} · {run.data_config.timeframe} ·{" "}
          {run.data_config.start_date} → {run.data_config.end_date}
        </p>
      </div>
      <div className="flex items-center gap-6 text-right">
        {run.status === "completed" && m ? (
          <>
            <div>
              <p className="text-small text-muted">Final</p>
              <p className="text-body text-ink">{fmtCurrency(m.final_value)}</p>
            </div>
            <div>
              <p className="text-small text-muted">Sharpe</p>
              <p className="text-body text-ink">{fmt(m.sharpe_ratio)}</p>
            </div>
            <div>
              <p className="text-small text-muted">Max DD</p>
              <p className={`text-body ${m.max_drawdown != null && m.max_drawdown < 0 ? "text-negative" : "text-ink"}`}>
                {fmtPct(m.max_drawdown)}
              </p>
            </div>
          </>
        ) : (
          <span className={`text-small font-medium ${statusColor[run.status]}`}>
            {run.status}
          </span>
        )}
      </div>
    </div>
  );
}
