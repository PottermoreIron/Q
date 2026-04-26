/**
 * Typed API client. All fetch calls go through here.
 * Token stored in memory (sessionStorage on web, AsyncStorage on mobile).
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// ── Case transformers ─────────────────────────────────────────────────────────

function snakeToCamelStr(s: string): string {
  return s.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

function camelToSnakeStr(s: string): string {
  return s.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function snakeToCamel(obj: unknown): any {
  if (Array.isArray(obj)) return obj.map(snakeToCamel);
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        snakeToCamelStr(k),
        snakeToCamel(v),
      ]),
    );
  }
  return obj;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function camelToSnake(obj: unknown): any {
  if (Array.isArray(obj)) return obj.map(camelToSnake);
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        camelToSnakeStr(k),
        camelToSnake(v),
      ]),
    );
  }
  return obj;
}

// ── HTTP helpers ──────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

async function requestCamel<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const raw = await request<unknown>(path, options, token);
  return snakeToCamel(raw) as T;
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export type User = { id: string; email: string; display_name: string; created_at: string };
export type TokenResponse = { access_token: string; token_type: string; user: User };

export const auth = {
  register: (body: { email: string; password: string; display_name: string }) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify(body) }),

  login: (body: { email: string; password: string }) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),

  me: (token: string) => request<User>("/auth/me", {}, token),
};

// ── Data ──────────────────────────────────────────────────────────────────────

export type AssetClass = "crypto" | "stock" | "forex" | "futures" | "options";
export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d" | "1w" | "1M";
export type DataSource = "csv" | "yahoo" | "binance" | "alpha_vantage" | "polygon" | "alpaca";

export type SymbolResult = {
  symbol: string;
  name: string;
  asset_class: AssetClass;
  exchange: string;
};

export type OHLCVBar = {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type DataPreview = {
  symbol: string;
  asset_class: AssetClass;
  timeframe: Timeframe;
  start_date: string;
  end_date: string;
  bar_count: number;
  bars: OHLCVBar[];
};

export type CSVUploadResult = {
  file_key: string;
  row_count: number;
  detected_symbol: string | null;
  detected_timeframe: string | null;
  columns: string[];
};

// ── Strategies ────────────────────────────────────────────────────────────────

export type StrategyBlock = {
  id: string;
  type: "indicator" | "condition" | "action" | "filter";
  name: string;
  params: Record<string, unknown>;
};

export type Strategy = {
  id: string;
  name: string;
  description: string | null;
  blocks: StrategyBlock[];
  python_code: string | null;
  user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ValidateResult = { valid: boolean; errors: string[] };
export type CompileResult = { python_code: string };

export const strategies = {
  list: (token?: string) =>
    request<Strategy[]>("/strategies", {}, token),

  get: (id: string, token?: string) =>
    request<Strategy>(`/strategies/${id}`, {}, token),

  create: (body: { name: string; blocks: StrategyBlock[]; description?: string; python_code?: string }, token?: string) =>
    request<Strategy>("/strategies", { method: "POST", body: JSON.stringify(body) }, token),

  update: (id: string, patch: Partial<{ name: string; description: string; blocks: StrategyBlock[]; python_code: string }>, token?: string) =>
    request<Strategy>(`/strategies/${id}`, { method: "PATCH", body: JSON.stringify(patch) }, token),

  delete: (id: string, token?: string) =>
    fetch(`${BASE_URL}/strategies/${id}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),

  compile: (blocks: StrategyBlock[]) =>
    request<CompileResult>("/strategies/compile", { method: "POST", body: JSON.stringify({ name: "_", blocks }) }),

  validate: (code: string) =>
    request<ValidateResult>("/strategies/validate", { method: "POST", body: JSON.stringify({ code }) }),
};

// ── Backtests ─────────────────────────────────────────────────────────────────
// Wire format: snake_case. TS surface: camelCase via snakeToCamel transformer.

export type DataConfig = {
  source: DataSource;
  symbol: string;
  assetClass: AssetClass;
  timeframe: Timeframe;
  startDate: string;
  endDate: string;
};

export type Metrics = {
  schemaVersion: number;
  // core
  finalValue: number | null;
  totalReturn: number | null;
  cagr: number | null;
  // risk
  volatility: number | null;
  downsideVolatility: number | null;
  sharpeRatio: number | null;
  sortinoRatio: number | null;
  var95: number | null;
  cvar95: number | null;
  maxDrawdown: number | null;
  maxDrawdownDurationDays: number | null;
  calmarRatio: number | null;
  // distribution
  omegaRatio: number | null;
  tailRatio: number | null;
  // trade quality
  winRate: number | null;
  totalTrades: number | null;
  profitFactor: number | null;
  avgWin: number | null;
  avgLoss: number | null;
  largestWin: number | null;
  largestLoss: number | null;
  avgTradeDurationBars: number | null;
  // exposure
  exposurePct: number | null;
  turnover: number | null;
};

export type Trade = {
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  side: string;
  fees: number;
  slippageCost: number;
  entryTime: string | null;
  exitTime: string | null;
  quantity: number | null;
  pnlPct: number | null;
  barsHeld: number | null;
  mae: number | null;
  mfe: number | null;
};

export type BacktestRun = {
  id: string;
  strategyId: string | null;
  strategyName: string;
  dataConfig: DataConfig;
  status: "pending" | "running" | "completed" | "failed";
  engine: string | null;
  metrics: Metrics | null;
  equityCurve: [string, number][] | null;
  trades: Trade[] | null;
  errorMessage: string | null;
  logOutput: string | null;
  asOfTime: string | null;
  createdAt: string;
  completedAt: string | null;
};

export const backtests = {
  create: (body: { strategyId: string; dataConfig: DataConfig }, token?: string) =>
    requestCamel<BacktestRun>("/backtests", {
      method: "POST",
      body: JSON.stringify(camelToSnake(body)),
    }, token),

  list: (strategyId?: string, token?: string) => {
    const qs = strategyId ? `?strategy_id=${strategyId}` : "";
    return requestCamel<BacktestRun[]>(`/backtests${qs}`, {}, token);
  },

  get: (id: string, token?: string) =>
    requestCamel<BacktestRun>(`/backtests/${id}`, {}, token),

  delete: (id: string, token?: string) =>
    fetch(`${BASE_URL}/backtests/${id}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),
};

export const data = {
  search: (q: string, asset_class?: AssetClass) => {
    const params = new URLSearchParams({ q });
    if (asset_class) params.set("asset_class", asset_class);
    return request<SymbolResult[]>(`/data/search?${params}`);
  },

  fetch: (params: {
    symbol: string;
    asset_class: AssetClass;
    timeframe: Timeframe;
    start_date: string;
    end_date: string;
  }) => {
    const qs = new URLSearchParams(params as Record<string, string>);
    return request<DataPreview>(`/data/fetch?${qs}`);
  },

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<CSVUploadResult>("/data/upload", {
      method: "POST",
      body: form,
      headers: {},  // let browser set Content-Type + boundary
    });
  },
};
