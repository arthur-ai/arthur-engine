export type SortOrder = "asc" | "desc";

export interface DatasetFilters {
  searchQuery?: string;
  sortOrder: SortOrder;
  page: number;
  pageSize: number;
}

// Column Default Value Types
export type ColumnDefaultType = "none" | "static" | "timestamp";

export interface ColumnDefaultConfig {
  type: ColumnDefaultType;
  value?: string; // Only used when type is "static"
}

export type ColumnDefaults = Record<string, ColumnDefaultConfig>;

export interface DatasetColumnConfigs {
  columnDefaults: ColumnDefaults;
}

// Helper functions
export function getColumnDefault(columnDefaults: ColumnDefaults | undefined, columnName: string): ColumnDefaultConfig {
  return columnDefaults?.[columnName] ?? { type: "none" };
}

export function getDefaultDisplayLabel(config: ColumnDefaultConfig): string {
  switch (config.type) {
    case "static":
      return config.value ? `"${config.value}"` : "Empty";
    case "timestamp":
      return "Timestamp";
    case "none":
    default:
      return "None";
  }
}
