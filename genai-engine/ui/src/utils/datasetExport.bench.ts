import { serialize_csv } from "csv-utils-wasm";
import Papa from "papaparse";
import { beforeAll, bench, describe, vi } from "vitest";

import { exportDatasetToCSV, exportDatasetToCSVWasm } from "./datasetExport";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";


const COLUMNS = ["prompt", "response", "context", "label", "score"];

function makeRows(count: number): DatasetVersionRowResponse[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `row-${i}`,
    created_at: Date.now(),
    data: COLUMNS.map((col) => ({
      column_name: col,
      column_value: `value-${i}-${col}`,
    })),
  }));
}

function toCsvObjects(rows: DatasetVersionRowResponse[]): Record<string, string>[] {
  return rows.map((row) => {
    const obj: Record<string, string> = {};
    row.data.forEach((col) => {
      obj[col.column_name] = col.column_value;
    });
    return obj;
  });
}

const rows1k = makeRows(1_000);
const rows10k = makeRows(10_000);
const csvObjects1k = toCsvObjects(rows1k);
const csvObjects10k = toCsvObjects(rows10k);

// Stub browser-only globals that exportDatasetToCSV calls.
// The actual CPU work is Papa.unparse + Blob construction; DOM calls are O(1).
beforeAll(() => {
  vi.stubGlobal("URL", {
    createObjectURL: vi.fn(() => "blob:mock"),
    revokeObjectURL: vi.fn(),
  });
  vi.stubGlobal(
    "Blob",
    class MockBlob {
      constructor(_parts: unknown[]) {}
    },
  );
  vi.stubGlobal("document", {
    createElement: vi.fn(() => ({
      href: "",
      download: "",
      click: vi.fn(),
    })),
    body: {
      appendChild: vi.fn(),
      removeChild: vi.fn(),
    },
  });
});

describe("Papa.unparse – serialize rows to CSV string", () => {
  bench("1K rows", () => {
    Papa.unparse(csvObjects1k);
  });

  bench("10K rows", () => {
    Papa.unparse(csvObjects10k);
  });
});

describe("exportDatasetToCSV – full pipeline (map + unparse + Blob + DOM stubs)", () => {
  bench("1K rows", () => {
    exportDatasetToCSV("dataset", rows1k);
  });

  bench("10K rows", () => {
    exportDatasetToCSV("dataset", rows10k);
  });
});

describe("serialize_csv vs Papa.unparse – 10K rows (TS vs WASM)", () => {
  bench("TS   – Papa.unparse", () => {
    Papa.unparse(csvObjects10k);
  });

  bench("WASM – serialize_csv", () => {
    serialize_csv(JSON.stringify(csvObjects10k));
  });
});

describe("exportDatasetToCSVWasm vs exportDatasetToCSV – full pipeline 10K (TS vs WASM)", () => {
  bench("TS  ", () => {
    exportDatasetToCSV("dataset", rows10k);
  });

  bench("WASM", () => {
    exportDatasetToCSVWasm("dataset", rows10k);
  });
});
