import Papa from "papaparse";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

export function exportDatasetToCSV(datasetName: string, rows: DatasetVersionRowResponse[]): void {
  try {
    const csvData = rows.map((row) => {
      const obj: Record<string, string> = {};
      row.data.forEach((col) => {
        obj[col.column_name] = col.column_value;
      });
      return obj;
    });

    const csv = Papa.unparse(csvData);

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${datasetName}-${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch {
    throw new Error("Failed to export dataset to CSV");
  }
}
