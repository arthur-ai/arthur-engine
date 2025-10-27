export function createEmptyRow(columns: string[]): Record<string, string> {
  const rowData: Record<string, string> = {};
  columns.forEach((col) => {
    rowData[col] = "";
  });
  return rowData;
}
