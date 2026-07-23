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

/**
 * Columns a new row is written against. A dataset that has no columns yet
 * (first addition) takes its initial schema from the selected transform's
 * variables — the same fallback the backend applies on bulk-add
 * (see bulk_add_traces_to_dataset in dataset_management_routes.py).
 */
export const resolveSchemaColumns = (datasetColumns: string[], transformVariables: TransformVariableDefinition[]): string[] =>
  datasetColumns.length > 0 ? datasetColumns : transformVariables.map((v) => v.variable_name);

export const addToDatasetFormOptions = formOptions({
  defaultValues: {
    dataset: "",
    transform: MANUAL_TRANSFORM_ID,
    columns: [] as Column[],
  },
});
