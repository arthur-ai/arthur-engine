import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

export function generateTempRowId(): string {
  return `temp-${Date.now()}-${Math.random()}`;
}

export function convertFromApiFormat(
  row: DatasetVersionRowResponse
): Record<string, unknown> {
  return Object.fromEntries(
    row.data.map((col) => [col.column_name, col.column_value])
  );
}
