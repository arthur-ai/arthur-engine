import { describe, expect, it } from "vitest";

import { datasetReducer, initialDatasetState } from "./reducer";

import type { DatasetVersionResponse } from "@/lib/api-client/api-client";

function makeVersion(overrides: Partial<DatasetVersionResponse>): DatasetVersionResponse {
  return {
    column_names: [],
    created_at: 0,
    dataset_id: "00000000-0000-0000-0000-000000000000",
    page: 0,
    page_size: 0,
    rows: [],
    total_count: 0,
    total_pages: 0,
    version_number: 0,
    ...overrides,
  };
}

describe("datasetReducer", () => {
  it("DATA/MERGE_CONFIGURED_COLUMNS sets columns on empty state without creating rows or pending changes", () => {
    const next = datasetReducer(initialDatasetState, {
      type: "DATA/MERGE_CONFIGURED_COLUMNS",
      payload: ["a", "b"],
    });

    expect(next.columns).toEqual(["a", "b"]);
    expect(next.rows).toEqual([]);
    expect(next.pendingChanges).toEqual({ added: [], updated: [], deleted: [] });
  });

  it("DATA/MERGE_CONFIGURED_COLUMNS merges without duplicating existing columns", () => {
    const state = { ...initialDatasetState, columns: ["a"] };
    const next = datasetReducer(state, {
      type: "DATA/MERGE_CONFIGURED_COLUMNS",
      payload: ["a", "b"],
    });

    expect(next.columns).toEqual(["a", "b"]);
  });

  it("DATA/LOAD_VERSION merges configured columns first, then appends version extras", () => {
    const next = datasetReducer(initialDatasetState, {
      type: "DATA/LOAD_VERSION",
      payload: makeVersion({ column_names: ["a", "c"], rows: [] }),
      configuredColumns: ["a", "b"],
    });

    expect(next.columns).toEqual(["a", "b", "c"]);
  });

  it("DATA/LOAD_VERSION with no configured columns is backward-compatible", () => {
    const next = datasetReducer(initialDatasetState, {
      type: "DATA/LOAD_VERSION",
      payload: makeVersion({ column_names: ["x"] }),
      configuredColumns: [],
    });

    expect(next.columns).toEqual(["x"]);
  });
});
