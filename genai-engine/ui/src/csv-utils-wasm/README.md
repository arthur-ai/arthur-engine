# csv-utils-wasm

A Rust/WebAssembly crate that provides CSV parsing, serialization, delimiter detection, and dataset row sorting for the Arthur Engine UI. Built with [wasm-pack](https://rustwasm.github.io/wasm-pack/) and integrated into the Vite build via [vite-plugin-wasm](https://github.com/Menci/vite-plugin-wasm).

---

## Problem Statement

The dataset management UI performs three CPU-bound operations entirely on the browser main thread:

1. **Row sorting** — `sortRows` in `src/utils/datasetSortUtils.ts` called `Array.find` inside the sort comparator. For a dataset with N rows and M columns per row, this is O(N × M × log N). At 10 K rows the sort took ~10.7 ms, locking the UI thread.

2. **CSV export** — `exportDatasetToCSV` used PapaParse's `Papa.unparse`, a JavaScript-only implementation, to serialize rows to a CSV string before triggering a browser download.

3. **CSV import** — `autoDetectDelimiter` made four sequential async PapaParse parses (one per candidate delimiter) to score which delimiter best fits the file. `parseCSVFull` and `parseCSVPreview` each made a single PapaParse pass over the `File` object.

The hypothesis was that Rust compiled to WASM could outperform the equivalent JavaScript for at least the sort case, where the algorithmic improvement (pre-extracting column values to eliminate the inner `Array.find`) would compound with faster native comparisons.

---

## Solution

A `wasm-bindgen` crate (`csv-utils-wasm`) compiled to `genai-engine/pkg/csv-utils-wasm/` and consumed by the UI as a local `file:` package dependency.

Four exported functions replace or augment the TypeScript equivalents:

| WASM function | Replaces | Key change |
|---|---|---|
| `sort_rows(values_json, ascending)` | `sortRows` comparator | Accepts pre-extracted values; returns `Uint32Array` of sorted indices. Eliminates `Array.find` from every comparison. |
| `serialize_csv(rows_json)` | `Papa.unparse` | Uses the Rust `csv` crate writer over a JSON-encoded row array. |
| `parse_csv(input, has_header, delimiter)` | `Papa.parse(string, …)` | Uses the Rust `csv` crate reader; returns JSON `{ columns, rows }`. |
| `detect_delimiter(preview)` | 4× `Papa.parse` in `autoDetectDelimiter` | Single synchronous pass over a string preview, scoring four candidate delimiters by column-count mean/variance. |

TypeScript wrapper functions (`sortRowsWasm`, `exportDatasetToCSVWasm`, `autoDetectDelimiterWasm`, `parseCSVFullWasm`, `parseCSVPreviewWasm`) expose the same call signatures as the originals so call sites required minimal changes. The original TS implementations are preserved for benchmarking comparison.

---

## Architecture

```
csv-utils-wasm/          ← this crate (source)
  Cargo.toml
  src/
    lib.rs               ← four #[wasm_bindgen] exported functions
    utils.rs             ← panic hook (console.error on panic)

genai-engine/pkg/
  csv-utils-wasm/        ← wasm-pack build output (bundler target)
    csv_utils_wasm.js    ← JS glue (wasm-bindgen generated)
    csv_utils_wasm_bg.js ← wasm-bindgen internals
    csv_utils_wasm_bg.wasm
    csv_utils_wasm.d.ts  ← TypeScript declarations

genai-engine/ui/
  package.json           ← "csv-utils-wasm": "file:../pkg/csv-utils-wasm"
  vite.config.ts         ← vite-plugin-wasm + vite-plugin-top-level-await
  vitest.config.ts       ← same plugins for bench WASM support
  src/
    utils/
      datasetSortUtils.ts         ← sortRows (TS) + sortRowsWasm (WASM)
      datasetExport.ts            ← exportDatasetToCSV (TS) + exportDatasetToCSVWasm (WASM)
      datasetSortUtils.bench.ts   ← TS vs WASM comparison benchmarks
      datasetExport.bench.ts      ← TS vs WASM comparison benchmarks
    components/datasets/import/
      csvParseUtils.ts            ← PapaParse originals + WASM variants
      csvParseUtils.bench.ts      ← TS vs WASM comparison benchmarks
```

### Data exchange pattern

Strings cross the WASM boundary cheaply (passed by reference in wasm-bindgen). For `sort_rows` specifically, the TS caller pre-extracts only the sort-column values into a JSON array before crossing the boundary, so only a thin slice of data is serialized — not the full row objects.

```
JS: rows.map(row => row.data.find(col => col.column_name === sortColumn)?.column_value ?? null)
  → JSON.stringify(values)          [O(N), one boundary crossing]
  → sort_rows(values_json, asc)     [Rust: O(N log N), O(1) comparisons]
  → Uint32Array of sorted indices
JS: indices.map(i => rows[i])       [O(N) reorder]
```

---

## Build

```bash
# From the crate root
cd genai-engine/ui/src/csv-utils-wasm
wasm-pack build --target bundler --out-dir ../../../pkg/csv-utils-wasm
```

The `--target bundler` flag produces ES module output compatible with Vite's static import of `.wasm` files.

After rebuilding, no `yarn install` is needed — the `file:` symlink in `node_modules` picks up changes automatically.

---

## Benchmark Results

Benchmarks run with Vitest 4.1 (`yarn bench`) on macOS, Node 20, Apple M-series. All timings are mean latency per operation.

### Sort — 10K rows, numeric column

| Implementation | Mean | ops/sec |
|---|---|---|
| TypeScript `sortRows` (Array.find in comparator) | 10.7 ms | 93 |
| WASM `sortRowsWasm` (pre-extracted indices) | 6.0 ms | 165 |

**WASM is 1.78× faster.** The gain comes from the algorithmic change (O(N log N) with O(1) comparisons vs O(N × M × log N)) rather than raw Rust speed. At smaller scales the JSON serialization overhead closes the gap.

### Sort — 10K rows, string column

| Implementation | Mean | ops/sec |
|---|---|---|
| TypeScript `sortRows` | 1.3 ms | 790 |
| WASM `sortRowsWasm` | 2.0 ms | 510 |

**TypeScript wins.** JavaScript's `localeCompare` is highly optimized by V8 for string data. The JSON serialization round-trip (~0.5 ms for 10K strings) is not recovered by Rust's byte-order `str::cmp`.

### CSV serialization — 10K rows, 5 columns

| Implementation | Mean | ops/sec |
|---|---|---|
| `Papa.unparse` (TypeScript) | 4.4 ms | 229 |
| WASM `serialize_csv` | 11.5 ms | 87 |

**TypeScript wins by 2.6×.** PapaParse is well-optimized JS. The mandatory `JSON.stringify` of the row objects before the WASM call (~4 ms for 10K rows) makes the WASM path inherently slower unless the data can be passed without re-serialization.

### CSV parsing — 10K rows, 5 columns

| Implementation | Mean | ops/sec |
|---|---|---|
| `Papa.parse` string (TypeScript) | 6.3 ms | 158 |
| WASM `parse_csv` | 12.6 ms | 79 |

**TypeScript wins by 2×.** PapaParse's incremental tokenizer avoids the JSON output serialization that the WASM function must perform to return structured data across the boundary.

### Post-parse validation — 10K rows

| Implementation | Mean | ops/sec |
|---|---|---|
| `validateParseResults` (TypeScript) | ~0.08 µs | 13M |

This function is not a bottleneck. It was benchmarked to confirm that no WASM port is warranted.

---

## Key Findings

**When WASM wins:** When the work done inside the WASM boundary is substantially larger than the serialization cost to get data in and results out — specifically when an algorithm changes complexity class (the sort case).

**When WASM loses:** When the WASM function must accept and return large structured data as JSON strings, the serialization round-trip dominates and eliminates any Rust execution advantage. This affected `serialize_csv` and `parse_csv`, where the boundary crossing cost (~4–11 ms) exceeded the computation savings.

**The boundary overhead for this codebase:**
- Passing a `&str` across the boundary is cheap (pointer + length, no copy for reads).
- Returning a `String` from Rust to JS is cheap (wasm-bindgen copies the bytes once).
- The real cost is `JSON.stringify` on the JS side before calling and `JSON.parse` on the JS side after returning, which scales linearly with data size.

**Practical takeaway:** The sort WASM function is a net improvement and has been adopted in the app (`selectors.ts`). The parse and serialize WASM functions remain available for comparison but the app continues to use the PapaParse-backed implementations for those paths.

**`detect_delimiter`** was not directly benchmarked against the original because the original uses async file I/O (measuring four sequential PapaParse file reads), whereas the WASM version operates on a pre-read string. The WASM version eliminates four Promise-wrapped PapaParse passes and replaces them with a single synchronous call, which is an unambiguous improvement in the import flow.
