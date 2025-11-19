import Papa from "papaparse";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { downloadFile } from "@/utils/fileDownload";

export function exportDatasetToCSV(datasetName: string, rows: DatasetVersionRowResponse[]): void {
  const csvData = rows.map((row) => {
    const obj: Record<string, string> = {};
    row.data.forEach((col) => {
      obj[col.column_name] = col.column_value;
    });
    return obj;
  });

  const csv = Papa.unparse(csvData);
  const timestamp = new Date().toISOString().split("T")[0];
  downloadFile(csv, `${datasetName}-${timestamp}.csv`, "text/csv;charset=utf-8;");
}
