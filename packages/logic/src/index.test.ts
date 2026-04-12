import { describe, it, expect } from "vitest";
import {
  StrategySchema,
  DataConfigSchema,
  BacktestRunSchema,
  BacktestMetricsSchema,
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

describe("BacktestMetricsSchema", () => {
  it("accepts null metrics for in-progress runs", () => {
    const result = BacktestMetricsSchema.safeParse({
      sharpeRatio: null,
      sortinoRatio: null,
      cagr: null,
      maxDrawdown: null,
      winRate: null,
      totalTrades: null,
      profitFactor: null,
      finalValue: null,
    });
    expect(result.success).toBe(true);
  });

  it("accepts complete metrics", () => {
    const result = BacktestMetricsSchema.safeParse({
      sharpeRatio: 2.41,
      sortinoRatio: 3.1,
      cagr: 0.47,
      maxDrawdown: -0.12,
      winRate: 0.62,
      totalTrades: 84,
      profitFactor: 2.1,
      finalValue: 147000,
    });
    expect(result.success).toBe(true);
  });
});
