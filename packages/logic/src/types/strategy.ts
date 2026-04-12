import { z } from "zod";

export const StrategyBlockTypeSchema = z.enum([
  "indicator",
  "condition",
  "action",
  "filter",
]);

export const StrategyBlockSchema = z.object({
  id: z.string().uuid(),
  type: StrategyBlockTypeSchema,
  name: z.string().min(1),
  params: z.record(z.unknown()),
});

export const StrategySchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  blocks: z.array(StrategyBlockSchema),
  pythonCode: z.string().optional(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export const CreateStrategySchema = StrategySchema.omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type StrategyBlockType = z.infer<typeof StrategyBlockTypeSchema>;
export type StrategyBlock = z.infer<typeof StrategyBlockSchema>;
export type Strategy = z.infer<typeof StrategySchema>;
export type CreateStrategy = z.infer<typeof CreateStrategySchema>;
