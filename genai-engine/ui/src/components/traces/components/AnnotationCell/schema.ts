import z from "zod";

import type { ContinuousEvalRunStatus } from "@/lib/api-client/api-client";

export const HumanAnnotation = z.object({
  id: z.string(),
  annotation_type: z.literal("human"),
  annotation_score: z.number(),
  annotation_description: z.string().optional(),
  trace_id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const ContinuousEvalAnnotation = z.object({
  annotation_type: z.literal("continuous_eval"),
  annotation_score: z.number(),
  annotation_description: z.string(),
  trace_id: z.string(),
  continuous_eval_id: z.string(),
  input_variables: z
    .array(
      z.object({
        name: z.string(),
        value: z.string(),
      })
    )
    .nullable(),
  cost: z.number(),
  run_status: z.string<ContinuousEvalRunStatus>(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const Annotation = z.discriminatedUnion("annotation_type", [HumanAnnotation, ContinuousEvalAnnotation]);

export type Annotation = z.infer<typeof Annotation>;
