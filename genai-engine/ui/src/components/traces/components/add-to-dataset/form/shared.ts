import { formOptions } from "@tanstack/react-form";
import type {
  DatasetTransformDefinition,
  DatasetTransformColumnDefinition,
  DatasetTransformResponse,
} from "@/lib/api-client/api-client";

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
export type TransformDefinition = DatasetTransformDefinition;
export type TransformColumnDefinition = DatasetTransformColumnDefinition;
export type DatasetTransform = DatasetTransformResponse;

export const addToDatasetFormOptions = formOptions({
  defaultValues: {
    dataset: "",
    transform: "manual",         // Selected transform ID or "manual"
    columns: [] as Column[],
  },
});
