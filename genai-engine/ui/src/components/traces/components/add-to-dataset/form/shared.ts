import { formOptions } from "@tanstack/react-form";

export type Column = {
  name: string;
  value: string;
  path: string;
  span_name?: string;
  attribute_path?: string;
};

export type TransformDefinition = {
  version: string;
  columns: Array<{
    column_name: string;
    span_name: string;
    attribute_path: string;
    fallback?: any;
  }>;
};

export interface DatasetTransform {
  id: string;
  dataset_id: string;
  name: string;
  description?: string | null;
  definition: TransformDefinition;
  created_at: number;  // Unix timestamp in milliseconds
  updated_at: number;  // Unix timestamp in milliseconds
}

export const addToDatasetFormOptions = formOptions({
  defaultValues: {
    dataset: "",
    transform: "manual",         // Selected transform ID or "manual"
    columns: [] as Column[],
  },
});
