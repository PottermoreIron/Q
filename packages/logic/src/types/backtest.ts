import { z } from "zod";
import { DataConfigSchema } from "./market-data";

export const BacktestStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
]);

export const BacktestMetricsSchema = z.object({
  sharpeRatio: z.number().nullable(),
  sortinoRatio: z.number().nullable(),
  cagr: z.number().nullable(),          // as decimal: 0.47 = 47%
  maxDrawdown: z.number().nullable(),   // as decimal: -0.12 = -12%
  winRate: z.number().nullable(),       // as decimal: 0.6 = 60%
  totalTrades: z.number().int().nullable(),
  profitFactor: z.number().nullable(),
  finalValue: z.number().nullable(),
});

export const BacktestRunSchema = z.object({
  id: z.string().uuid(),
  strategyId: z.string().uuid(),
  strategyName: z.string(),
  dataConfig: DataConfigSchema,
  status: BacktestStatusSchema,
  engine: z.enum(["vectorbt", "backtrader"]).optional(),
  metrics: BacktestMetricsSchema.optional(),
  errorMessage: z.string().optional(),
  createdAt: z.string().datetime(),
  completedAt: z.string().datetime().optional(),
});

export const CreateBacktestRunSchema = BacktestRunSchema.pick({
  strategyId: true,
  dataConfig: true,
});

export type BacktestStatus = z.infer<typeof BacktestStatusSchema>;
export type BacktestMetrics = z.infer<typeof BacktestMetricsSchema>;
export type BacktestRun = z.infer<typeof BacktestRunSchema>;
export type CreateBacktestRun = z.infer<typeof CreateBacktestRunSchema>;
