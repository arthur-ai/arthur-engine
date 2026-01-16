import type { ModelProvider } from "@/lib/api-client/api-client";

export interface GenerationConfig {
  datasetPurpose: string;
  columnDescriptions: { columnName: string; description: string }[];
  numRows: number;
  modelProvider: ModelProvider;
  modelName: string;
  temperature?: number;
}

export interface SyntheticRow {
  id: string;
  data: Record<string, string>;
  status: "generated" | "modified" | "added";
}
