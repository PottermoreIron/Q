/**
 * Mobile API client — mirrors apps/web/src/lib/api.ts.
 * React Native's global fetch is used; no Node polyfills needed.
 */

const BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, (body as { detail?: string }).detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type Strategy = {
  id: string;
  name: string;
  description: string | null;
  blocks: unknown[];
  python_code: string | null;
  user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type DataConfig = {
  source: string;
  symbol: string;
  asset_class: string;
  timeframe: string;
  start_date: string;
  end_date: string;
};

export type Metrics = {
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  cagr: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  total_trades: number | null;
  profit_factor: number | null;
  final_value: number | null;
};

export type Trade = {
  entry_price: number;
  exit_price: number;
  pnl: number;
  side: string;
};

export type BacktestRun = {
  id: string;
  strategy_id: string | null;
  strategy_name: string;
  data_config: DataConfig;
  status: "pending" | "running" | "completed" | "failed";
  engine: string | null;
  metrics: Metrics | null;
  equity_curve: [string, number][] | null;
  trades: Trade[] | null;
  error_message: string | null;
  log_output: string | null;
  created_at: string;
  completed_at: string | null;
};

// ── Endpoints ─────────────────────────────────────────────────────────────────

export const strategies = {
  list: (token?: string) => request<Strategy[]>("/strategies", {}, token),

  get: (id: string, token?: string) => request<Strategy>(`/strategies/${id}`, {}, token),

  create: (
    body: { name: string; blocks: unknown[]; description?: string; python_code?: string },
    token?: string,
  ) => request<Strategy>("/strategies", { method: "POST", body: JSON.stringify(body) }, token),

  update: (
    id: string,
    patch: Partial<{ name: string; description: string; blocks: unknown[]; python_code: string }>,
    token?: string,
  ) =>
    request<Strategy>(
      `/strategies/${id}`,
      { method: "PATCH", body: JSON.stringify(patch) },
      token,
    ),
};

export const backtests = {
  create: (
    body: { strategy_id: string; data_config: DataConfig },
    token?: string,
  ) =>
    request<BacktestRun>("/backtests", { method: "POST", body: JSON.stringify(body) }, token),

  list: (token?: string) => request<BacktestRun[]>("/backtests", {}, token),

  get: (id: string, token?: string) => request<BacktestRun>(`/backtests/${id}`, {}, token),
};
