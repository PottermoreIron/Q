import { z } from "zod";
import { DataConfigSchema } from "./market-data";

export const BacktestStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
]);

export const EngineHintSchema = z.enum(["simple", "vectorbt", "backtrader"]);

export const MetricsSchema = z.object({
  schemaVersion:           z.literal(2).default(2),
  // core
  finalValue:              z.number().nullable(),
  totalReturn:             z.number().nullable(),
  cagr:                    z.number().nullable(),
  // risk
  volatility:              z.number().nullable(),
  downsideVolatility:      z.number().nullable(),
  sharpeRatio:             z.number().nullable(),
  sortinoRatio:            z.number().nullable(),
  var95:                   z.number().nullable(),
  cvar95:                  z.number().nullable(),
  maxDrawdown:             z.number().nullable(),
  maxDrawdownDurationDays: z.number().int().nullable(),
  calmarRatio:             z.number().nullable(),
  // distribution
  omegaRatio:              z.number().nullable(),
  tailRatio:               z.number().nullable(),
  // trade quality
  winRate:                 z.number().nullable(),
  totalTrades:             z.number().int().nullable(),
  profitFactor:            z.number().nullable(),
  avgWin:                  z.number().nullable(),
  avgLoss:                 z.number().nullable(),
  largestWin:              z.number().nullable(),
  largestLoss:             z.number().nullable(),
  avgTradeDurationBars:    z.number().nullable(),
  // exposure
  exposurePct:             z.number().nullable(),
  turnover:                z.number().nullable(),
});

// backward-compat alias
export const BacktestMetricsSchema = MetricsSchema;

export const TradeSchema = z.object({
  // v1
  entryPrice:   z.number(),
  exitPrice:    z.number(),
  pnl:          z.number(),
  side:         z.string(),
  fees:         z.number().default(0),
  slippageCost: z.number().default(0),
  // v2
  entryTime:    z.string().nullish(),
  exitTime:     z.string().nullish(),
  quantity:     z.number().nullish(),
  pnlPct:       z.number().nullish(),
  barsHeld:     z.number().int().nullish(),
  mae:          z.number().nullish(),
  mfe:          z.number().nullish(),
});

export const BacktestRunSchema = z.object({
  id:           z.string().uuid(),
  strategyId:   z.string().uuid().nullable(),
  strategyName: z.string(),
  dataConfig:   DataConfigSchema,
  status:       BacktestStatusSchema,
  engine:       EngineHintSchema.optional(),
  metrics:      MetricsSchema.nullable().optional(),
  equityCurve:  z.array(z.tuple([z.string(), z.number()])).nullable().optional(),
  trades:       z.array(TradeSchema).nullable().optional(),
  errorMessage: z.string().nullable().optional(),
  logOutput:    z.string().nullable().optional(),
  asOfTime:     z.string().nullable().optional(),
  createdAt:    z.string().datetime(),
  completedAt:  z.string().datetime().nullable().optional(),
});

export const CreateBacktestRunSchema = z.object({
  strategyId: z.string().uuid(),
  dataConfig: DataConfigSchema,
});

export type BacktestStatus    = z.infer<typeof BacktestStatusSchema>;
export type EngineHint        = z.infer<typeof EngineHintSchema>;
export type Metrics           = z.infer<typeof MetricsSchema>;
export type BacktestMetrics   = Metrics; // backward-compat alias
export type Trade             = z.infer<typeof TradeSchema>;
export type BacktestRun       = z.infer<typeof BacktestRunSchema>;
export type CreateBacktestRun = z.infer<typeof CreateBacktestRunSchema>;
