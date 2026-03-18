import { sort_rows } from "csv-utils-wasm";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

export function sortRows(rows: DatasetVersionRowResponse[], sortColumn: string | null, sortDirection: "asc" | "desc"): DatasetVersionRowResponse[] {
  if (!sortColumn) return rows;

  return [...rows].sort((a, b) => {
    const aCol = a.data.find((col) => col.column_name === sortColumn);
    const bCol = b.data.find((col) => col.column_name === sortColumn);

    const aVal = aCol?.column_value;
    const bVal = bCol?.column_value;

    if (!aVal) return 1;
    if (!bVal) return -1;

    const aNum = Number(aVal);
    const bNum = Number(bVal);
    if (!isNaN(aNum) && !isNaN(bNum)) {
      return sortDirection === "asc" ? aNum - bNum : bNum - aNum;
    }

    const comparison = aVal.localeCompare(bVal);
    return sortDirection === "asc" ? comparison : -comparison;
  });
}

export function sortRowsWasm(
  rows: DatasetVersionRowResponse[],
  sortColumn: string | null,
  sortDirection: "asc" | "desc",
): DatasetVersionRowResponse[] {
  if (!sortColumn) return rows;

  const values = rows.map((row) => row.data.find((col) => col.column_name === sortColumn)?.column_value ?? null);
  const indices = sort_rows(JSON.stringify(values), sortDirection === "asc");
  return Array.from(indices).map((i) => rows[i]);
}
