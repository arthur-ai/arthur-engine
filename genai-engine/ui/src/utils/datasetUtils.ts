/**
 * Extract column names from dataset metadata
 */
export function getColumnNames(
  metadata: Record<string, unknown> | null | undefined
): string[] {
  if (!metadata || typeof metadata !== "object") return [];
  const columns = (metadata as { columns?: unknown }).columns;
  return Array.isArray(columns) ? columns : [];
}

/**
 * Create empty row data from column names
 */
export function createEmptyRow(columns: string[]): Record<string, string> {
  const rowData: Record<string, string> = {};
  columns.forEach((col) => {
    rowData[col] = "";
  });
  return rowData;
}
