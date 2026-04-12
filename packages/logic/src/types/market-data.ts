import { z } from "zod";

export const AssetClassSchema = z.enum([
  "crypto",
  "stock",
  "forex",
  "futures",
  "options",
]);

export const TimeframeSchema = z.enum([
  "1m", "5m", "15m", "30m",
  "1h", "4h",
  "1d", "1w", "1M",
]);

export const DataSourceSchema = z.enum([
  "csv",
  "yahoo",
  "binance",
  "alpha_vantage",
  "polygon",
  "alpaca",
]);

export const OHLCVSchema = z.object({
  timestamp: z.number(), // Unix ms
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  volume: z.number(),
});

export const DataConfigSchema = z.object({
  source: DataSourceSchema,
  symbol: z.string().min(1),
  assetClass: AssetClassSchema,
  timeframe: TimeframeSchema,
  startDate: z.string().date(),
  endDate: z.string().date(),
});

export type AssetClass = z.infer<typeof AssetClassSchema>;
export type Timeframe = z.infer<typeof TimeframeSchema>;
export type DataSource = z.infer<typeof DataSourceSchema>;
export type OHLCV = z.infer<typeof OHLCVSchema>;
export type DataConfig = z.infer<typeof DataConfigSchema>;
