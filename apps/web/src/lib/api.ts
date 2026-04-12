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
