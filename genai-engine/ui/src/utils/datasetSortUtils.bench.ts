import { bench, describe } from "vitest";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

import { sortRows, sortRowsWasm } from "./datasetSortUtils";

const COLUMNS = ["id", "name", "value", "category", "score"];

function makeRows(count: number): DatasetVersionRowResponse[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `row-${i}`,
    created_at: Date.now(),
    data: COLUMNS.map((col) => ({
      column_name: col,
      column_value: col === "score" ? String(Math.random() * 1000) : `value-${i}-${col}`,
    })),
  }));
}

const rows100 = makeRows(100);
const rows1k = makeRows(1_000);
const rows10k = makeRows(10_000);

describe("sortRows – numeric column (score)", () => {
  bench("100 rows asc", () => {
    sortRows(rows100, "score", "asc");
  });

  bench("1K rows asc", () => {
    sortRows(rows1k, "score", "asc");
  });

  bench("10K rows asc", () => {
    sortRows(rows10k, "score", "asc");
  });

  bench("10K rows desc", () => {
    sortRows(rows10k, "score", "desc");
  });
});

describe("sortRows – string column (name)", () => {
  bench("100 rows asc", () => {
    sortRows(rows100, "name", "asc");
  });

  bench("1K rows asc", () => {
    sortRows(rows1k, "name", "asc");
  });

  bench("10K rows asc", () => {
    sortRows(rows10k, "name", "asc");
  });

  bench("10K rows desc", () => {
    sortRows(rows10k, "name", "desc");
  });
});

describe("sortRowsWasm vs sortRows – numeric 10K (TS vs WASM)", () => {
  bench("TS  – 10K asc", () => {
    sortRows(rows10k, "score", "asc");
  });

  bench("WASM – 10K asc", () => {
    sortRowsWasm(rows10k, "score", "asc");
  });

  bench("TS  – 10K desc", () => {
    sortRows(rows10k, "score", "desc");
  });

  bench("WASM – 10K desc", () => {
    sortRowsWasm(rows10k, "score", "desc");
  });
});

describe("sortRowsWasm vs sortRows – string 10K (TS vs WASM)", () => {
  bench("TS  – 10K asc", () => {
    sortRows(rows10k, "name", "asc");
  });

  bench("WASM – 10K asc", () => {
    sortRowsWasm(rows10k, "name", "asc");
  });
});
