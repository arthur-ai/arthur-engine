import { parse_csv } from "csv-utils-wasm";
import Papa from "papaparse";
import { beforeAll, bench, describe } from "vitest";

import { DEFAULT_CONFIG } from "./csvImportConstants";
import { validateParseResults } from "./csvParseUtils";

const COLUMNS = ["prompt", "response", "context", "label", "score"];

function makeCsvString(rowCount: number): string {
  const header = COLUMNS.join(",");
  const rows = Array.from({ length: rowCount }, (_, i) => COLUMNS.map((col) => `value-${i}-${col}`).join(","));
  return [header, ...rows].join("\n");
}

function parseCsvString(csv: string): Promise<{ columns: string[]; rows: Record<string, string>[] }> {
  return new Promise((resolve) => {
    Papa.parse(csv, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        resolve({
          columns: results.meta.fields ?? [],
          rows: results.data as Record<string, string>[],
        });
      },
    });
  });
}

const csv100 = makeCsvString(100);
const csv1k = makeCsvString(1_000);
const csv10k = makeCsvString(10_000);

describe("Papa.parse – CSV string to rows", () => {
  bench("100 rows", async () => {
    await parseCsvString(csv100);
  });

  bench("1K rows", async () => {
    await parseCsvString(csv1k);
  });

  bench("10K rows", async () => {
    await parseCsvString(csv10k);
  });
});

describe("validateParseResults – post-parse validation", () => {
  let columns: string[] = [];
  let rows: Record<string, string>[] = [];

  beforeAll(async () => {
    const result = await parseCsvString(csv10k);
    columns = result.columns;
    rows = result.rows;
  });

  bench("10K rows", () => {
    validateParseResults(columns, rows, [], DEFAULT_CONFIG, 0);
  });
});

describe("parse_csv vs Papa.parse – CSV string to rows (TS vs WASM)", () => {
  bench("TS   – Papa.parse 1K rows", async () => {
    await parseCsvString(csv1k);
  });

  bench("WASM – parse_csv  1K rows", () => {
    parse_csv(csv1k, true, ",");
  });

  bench("TS   – Papa.parse 10K rows", async () => {
    await parseCsvString(csv10k);
  });

  bench("WASM – parse_csv  10K rows", () => {
    parse_csv(csv10k, true, ",");
  });
});
