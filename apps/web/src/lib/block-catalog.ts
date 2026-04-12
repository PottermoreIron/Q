import type { StrategyBlock } from "./api";

export type BlockDef = {
  type: StrategyBlock["type"];
  name: string;
  label: string;
  description: string;
  defaultParams: Record<string, unknown>;
  paramDefs: ParamDef[];
};

export type ParamDef = {
  key: string;
  label: string;
  type: "number" | "select";
  default: unknown;
  options?: { value: unknown; label: string }[];
  min?: number;
  max?: number;
};

export const BLOCK_CATALOG: BlockDef[] = [
  // ── Indicators ─────────────────────────────────────────────────────────────
  {
    type: "indicator", name: "ema", label: "EMA",
    description: "Exponential Moving Average",
    defaultParams: { period: 20 },
    paramDefs: [{ key: "period", label: "Period", type: "number", default: 20, min: 2, max: 500 }],
  },
  {
    type: "indicator", name: "sma", label: "SMA",
    description: "Simple Moving Average",
    defaultParams: { period: 50 },
    paramDefs: [{ key: "period", label: "Period", type: "number", default: 50, min: 2, max: 500 }],
  },
  {
    type: "indicator", name: "rsi", label: "RSI",
    description: "Relative Strength Index",
    defaultParams: { period: 14 },
    paramDefs: [{ key: "period", label: "Period", type: "number", default: 14, min: 2, max: 100 }],
  },
  {
    type: "indicator", name: "macd", label: "MACD",
    description: "Moving Average Convergence Divergence",
    defaultParams: { fast: 12, slow: 26, signal: 9 },
    paramDefs: [
      { key: "fast",   label: "Fast",   type: "number", default: 12, min: 2, max: 100 },
      { key: "slow",   label: "Slow",   type: "number", default: 26, min: 2, max: 200 },
      { key: "signal", label: "Signal", type: "number", default:  9, min: 2, max: 50  },
    ],
  },
  {
    type: "indicator", name: "bbands", label: "Bollinger Bands",
    description: "Bollinger Bands (upper / mid / lower)",
    defaultParams: { period: 20, std_dev: 2 },
    paramDefs: [
      { key: "period",  label: "Period",  type: "number", default: 20,  min: 2, max: 200 },
      { key: "std_dev", label: "Std Dev", type: "number", default:  2,  min: 0.5, max: 5 },
    ],
  },
  {
    type: "indicator", name: "atr", label: "ATR",
    description: "Average True Range",
    defaultParams: { period: 14 },
    paramDefs: [{ key: "period", label: "Period", type: "number", default: 14, min: 2, max: 100 }],
  },

  // ── Conditions ─────────────────────────────────────────────────────────────
  {
    type: "condition", name: "ema_crossover", label: "EMA Crossover",
    description: "Enter when fast EMA crosses above slow EMA",
    defaultParams: { fast_period: 10, slow_period: 30 },
    paramDefs: [
      { key: "fast_period", label: "Fast Period", type: "number", default: 10, min: 2, max: 200 },
      { key: "slow_period", label: "Slow Period", type: "number", default: 30, min: 2, max: 500 },
    ],
  },
  {
    type: "condition", name: "sma_crossover", label: "SMA Crossover",
    description: "Enter when fast SMA crosses above slow SMA",
    defaultParams: { fast_period: 20, slow_period: 50 },
    paramDefs: [
      { key: "fast_period", label: "Fast Period", type: "number", default: 20, min: 2, max: 200 },
      { key: "slow_period", label: "Slow Period", type: "number", default: 50, min: 2, max: 500 },
    ],
  },
  {
    type: "condition", name: "rsi_mean_reversion", label: "RSI Mean Reversion",
    description: "Enter on oversold, exit on overbought",
    defaultParams: { period: 14, oversold: 30, overbought: 70 },
    paramDefs: [
      { key: "period",     label: "Period",     type: "number", default: 14, min: 2, max: 100 },
      { key: "oversold",   label: "Oversold",   type: "number", default: 30, min: 5, max: 49  },
      { key: "overbought", label: "Overbought", type: "number", default: 70, min: 51, max: 95 },
    ],
  },
  {
    type: "condition", name: "macd_crossover", label: "MACD Crossover",
    description: "Enter when MACD histogram crosses above zero",
    defaultParams: {},
    paramDefs: [],
  },
  {
    type: "condition", name: "bollinger_breakout", label: "Bollinger Breakout",
    description: "Enter on upper band breakout, exit at midline",
    defaultParams: {},
    paramDefs: [],
  },
  {
    type: "condition", name: "bollinger_mean_reversion", label: "Bollinger Reversion",
    description: "Enter at lower band, exit at midline",
    defaultParams: {},
    paramDefs: [],
  },
  {
    type: "condition", name: "price_above_sma", label: "Price Above SMA",
    description: "Enter when price crosses above SMA, exit below",
    defaultParams: { period: 200 },
    paramDefs: [{ key: "period", label: "Period", type: "number", default: 200, min: 2, max: 500 }],
  },

  // ── Actions ────────────────────────────────────────────────────────────────
  {
    type: "action", name: "stop_loss", label: "Stop Loss",
    description: "Exit position on loss threshold",
    defaultParams: { percent: 5 },
    paramDefs: [{ key: "percent", label: "Loss %", type: "number", default: 5, min: 0.1, max: 50 }],
  },
  {
    type: "action", name: "take_profit", label: "Take Profit",
    description: "Exit position on profit target",
    defaultParams: { percent: 10 },
    paramDefs: [{ key: "percent", label: "Profit %", type: "number", default: 10, min: 0.1, max: 200 }],
  },
];

export const BLOCK_BY_NAME = Object.fromEntries(BLOCK_CATALOG.map((b) => [b.name, b]));

export const BLOCKS_BY_TYPE = {
  indicator: BLOCK_CATALOG.filter((b) => b.type === "indicator"),
  condition: BLOCK_CATALOG.filter((b) => b.type === "condition"),
  action:    BLOCK_CATALOG.filter((b) => b.type === "action"),
};
