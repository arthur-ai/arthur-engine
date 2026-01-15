import type { ColumnDefaults } from "@/types/dataset";

export function createEmptyRow(columns: string[], columnDefaults?: ColumnDefaults): Record<string, string> {
  const rowData: Record<string, string> = {};
  columns.forEach((col) => {
    const config = columnDefaults?.[col];
    if (config?.type === "static") {
      rowData[col] = config.value ?? "";
    } else if (config?.type === "timestamp") {
      rowData[col] = new Date().toISOString();
    } else {
      rowData[col] = "";
    }
  });
  return rowData;
}
