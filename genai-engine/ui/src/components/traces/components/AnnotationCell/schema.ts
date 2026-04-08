import z from "zod";

import type { AgenticAnnotationResponse, ContinuousEvalRunStatus } from "@/lib/api-client/api-client";

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
  id: z.string(),
  annotation_type: z.literal("continuous_eval"),
  annotation_score: z.number().optional(),
  annotation_description: z.string().optional(),
  trace_id: z.string().optional(),
  continuous_eval_id: z.string().optional(),
  eval_type: z.string().optional(),
  eval_name: z.string().optional(),
  eval_version: z.number().optional(),
  input_variables: z
    .array(
      z.object({
        name: z.string(),
        value: z.string(),
      })
    )
    .optional(),
  cost: z.number().optional(),
  run_status: z.string<ContinuousEvalRunStatus>(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const Annotation = z.discriminatedUnion("annotation_type", [HumanAnnotation, ContinuousEvalAnnotation]);

export type Annotation = z.infer<typeof Annotation>;

export type ContinuousEvalAnnotation = z.infer<typeof ContinuousEvalAnnotation>;
export type HumanAnnotation = z.infer<typeof HumanAnnotation>;

export const isContinuousEvalAnnotation = (annotation: Annotation): annotation is ContinuousEvalAnnotation =>
  annotation.annotation_type === "continuous_eval";

export const parseAnnotations = (annotations: AgenticAnnotationResponse[]): Annotation[] => {
  return annotations
    .map((annotation) => {
      const parsed = Annotation.safeParse(annotation);
      if (!parsed.success) return;

      return parsed.data;
    })
    .filter((annotation): annotation is Annotation => Boolean(annotation));
};
