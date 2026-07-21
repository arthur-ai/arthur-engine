import { describe, expect, it } from "vitest";

import { datasetReducer, initialDatasetState } from "./reducer";
import { selectHasUnsavedChanges, selectHasUnsavedWork } from "./selectors";

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

describe("datasetReducer columnsDirty", () => {
  it("marks columns dirty when columns are configured on a dataset with no rows", () => {
    const next = datasetReducer(initialDatasetState, {
      type: "DATA/SET_COLUMNS",
      payload: ["a", "b"],
    });

    expect(next.columns).toEqual(["a", "b"]);
    expect(next.columnsDirty).toBe(true);
    expect(next.pendingChanges).toEqual({ added: [], updated: [], deleted: [] });
  });

  it("does not mark columns dirty when the configured columns are unchanged", () => {
    const state = { ...initialDatasetState, columns: ["a", "b"] };
    const next = datasetReducer(state, {
      type: "DATA/SET_COLUMNS",
      payload: ["a", "b"],
    });

    expect(next.columnsDirty).toBe(false);
  });

  it("resets columnsDirty when a version is loaded from the server", () => {
    const dirty = { ...initialDatasetState, columnsDirty: true };
    const next = datasetReducer(dirty, {
      type: "DATA/LOAD_VERSION",
      payload: makeVersion({ column_names: ["a"] }),
    });

    expect(next.columnsDirty).toBe(false);
  });

  it("resets columnsDirty when changes are cleared", () => {
    const dirty = { ...initialDatasetState, columnsDirty: true };
    const next = datasetReducer(dirty, { type: "DATA/CLEAR_CHANGES" });

    expect(next.columnsDirty).toBe(false);
  });
});

describe("unsaved-work selectors", () => {
  it("treats unsaved column config as unsaved work, but not as a saveable (row) change", () => {
    const state = { ...initialDatasetState, columns: ["a"], columnsDirty: true };

    expect(selectHasUnsavedWork(state)).toBe(true);
    expect(selectHasUnsavedChanges(state)).toBe(false);
  });
});
