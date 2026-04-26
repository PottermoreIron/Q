import { describe, it, expect } from "vitest";
import {
  StrategySchema,
  DataConfigSchema,
  BacktestRunSchema,
  MetricsSchema,
  BacktestMetricsSchema,
  TradeSchema,
} from "./index";

describe("StrategySchema", () => {
  it("accepts a valid strategy", () => {
    const result = StrategySchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      name: "EMA Crossover",
      blocks: [],
      createdAt: "2024-01-01T00:00:00Z",
      updatedAt: "2024-01-01T00:00:00Z",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a strategy with empty name", () => {
    const result = StrategySchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      name: "",
      blocks: [],
      createdAt: "2024-01-01T00:00:00Z",
      updatedAt: "2024-01-01T00:00:00Z",
    });
    expect(result.success).toBe(false);
  });
});

describe("DataConfigSchema", () => {
  it("accepts a valid crypto config", () => {
    const result = DataConfigSchema.safeParse({
      source: "binance",
      symbol: "BTC/USDT",
      assetClass: "crypto",
      timeframe: "1d",
      startDate: "2022-01-01",
      endDate: "2023-12-31",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an unknown timeframe", () => {
    const result = DataConfigSchema.safeParse({
      source: "yahoo",
      symbol: "AAPL",
      assetClass: "stock",
      timeframe: "2d", // invalid
      startDate: "2022-01-01",
      endDate: "2023-12-31",
    });
    expect(result.success).toBe(false);
  });
});

describe("MetricsSchema", () => {
  it("accepts all-null metrics for in-progress runs", () => {
    const result = MetricsSchema.safeParse({
      schemaVersion: 2,
      sharpeRatio: null, sortinoRatio: null, cagr: null, maxDrawdown: null,
      winRate: null, totalTrades: null, profitFactor: null, finalValue: null,
      totalReturn: null, volatility: null, downsideVolatility: null,
      var95: null, cvar95: null, maxDrawdownDurationDays: null,
      calmarRatio: null, omegaRatio: null, tailRatio: null,
      avgWin: null, avgLoss: null, largestWin: null, largestLoss: null,
      avgTradeDurationBars: null, exposurePct: null, turnover: null,
    });
    expect(result.success).toBe(true);
  });

  it("accepts complete v2 metrics", () => {
    const result = MetricsSchema.safeParse({
      schemaVersion: 2,
      finalValue: 147000, totalReturn: 0.47, cagr: 0.39,
      volatility: 0.18, downsideVolatility: 0.12,
      sharpeRatio: 2.41, sortinoRatio: 3.1,
      var95: 0.02, cvar95: 0.03,
      maxDrawdown: -0.12, maxDrawdownDurationDays: 45, calmarRatio: 3.25,
      omegaRatio: 2.1, tailRatio: 1.3,
      winRate: 0.62, totalTrades: 84, profitFactor: 2.1,
      avgWin: 1200, avgLoss: 600, largestWin: 5000, largestLoss: -1200,
      avgTradeDurationBars: 8.5, exposurePct: 0.42, turnover: 0.67,
    });
    expect(result.success).toBe(true);
  });

  it("rejects schemaVersion != 2", () => {
    const result = MetricsSchema.safeParse({
      schemaVersion: 1,
      sharpeRatio: null, sortinoRatio: null, cagr: null, maxDrawdown: null,
      winRate: null, totalTrades: null, profitFactor: null, finalValue: null,
      totalReturn: null, volatility: null, downsideVolatility: null,
      var95: null, cvar95: null, maxDrawdownDurationDays: null,
      calmarRatio: null, omegaRatio: null, tailRatio: null,
      avgWin: null, avgLoss: null, largestWin: null, largestLoss: null,
      avgTradeDurationBars: null, exposurePct: null, turnover: null,
    });
    expect(result.success).toBe(false);
  });

  it("BacktestMetricsSchema is the same as MetricsSchema (alias)", () => {
    expect(BacktestMetricsSchema).toBe(MetricsSchema);
  });
});

describe("TradeSchema", () => {
  it("accepts a minimal v1 trade", () => {
    const result = TradeSchema.safeParse({
      entryPrice: 100, exitPrice: 115, pnl: 1500, side: "long",
    });
    expect(result.success).toBe(true);
  });

  it("accepts a full v2 trade", () => {
    const result = TradeSchema.safeParse({
      entryPrice: 100, exitPrice: 115, pnl: 1500, side: "long",
      fees: 5, slippageCost: 1,
      entryTime: "2023-01-03T00:00:00", exitTime: "2023-01-06T00:00:00",
      quantity: 10, pnlPct: 0.15, barsHeld: 3, mae: -0.10, mfe: 0.20,
    });
    expect(result.success).toBe(true);
  });
});
