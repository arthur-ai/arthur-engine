import { formOptions } from "@tanstack/react-form";

import type { TraceTransformDefinition, TraceTransformVariableDefinition, TraceTransformResponse } from "@/lib/api-client/api-client";

export type Column = {
  name: string;
  value: string;
  path: string;
  span_name?: string;
  attribute_path?: string;
  matchCount?: number;
  selectedSpanId?: string;
  allMatches?: Array<{
    span_id: string;
    span_name: string;
    extractedValue: string;
  }>;
};

// Re-export API types for convenience
export type TransformDefinition = TraceTransformDefinition;
export type TransformVariableDefinition = TraceTransformVariableDefinition;
export type TraceTransform = TraceTransformResponse;

export const MANUAL_TRANSFORM_ID = "manual";

export const hasSelectedTransform = (transformId: string): boolean => transformId !== "" && transformId !== MANUAL_TRANSFORM_ID;

export const addToDatasetFormOptions = formOptions({
  defaultValues: {
    dataset: "",
    transform: MANUAL_TRANSFORM_ID,
    columns: [] as Column[],
  },
});
