import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDeepLinkedRow } from "./useDeepLinkedRow";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

vi.mock("@/services/analytics", () => ({
  track: vi.fn(),
}));

const mocks = vi.hoisted(() => ({
  useApiQuery: vi.fn(),
}));

vi.mock("@/hooks/useApiQuery", () => ({
  useApiQuery: mocks.useApiQuery,
}));

const makeRow = (i: number): DatasetVersionRowResponse => ({ id: `row-${i}`, data: [], created_at: 0 });
const allRows = Array.from({ length: 60 }, (_, i) => makeRow(i));

type HookProps = Parameters<typeof useDeepLinkedRow>[0];

const baseProps: HookProps = {
  datasetId: "ds-1",
  rowId: "row-30",
  taskId: "task-1",
  currentVersion: 3,
  rowsPerPage: 25,
  currentPage: 0,
  dispatch: vi.fn(),
};

describe("useDeepLinkedRow", () => {
  beforeEach(() => {
    mocks.useApiQuery.mockReturnValue({ data: { rows: allRows } });
  });

  afterEach(cleanup);

  it("jumps to the located page and highlights the row", async () => {
    const dispatch = vi.fn();
    const { result } = renderHook((props: HookProps) => useDeepLinkedRow(props), {
      initialProps: { ...baseProps, dispatch },
    });

    // row-30 with 25 rows per page lives on page 1
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "VIEW/SET_PAGE", payload: 1 }));
    expect(result.current.highlightedRowId).toBe("row-30");
  });

  it("highlights without paginating when the row is already on the current page", async () => {
    const dispatch = vi.fn();
    const { result } = renderHook((props: HookProps) => useDeepLinkedRow(props), {
      initialProps: { ...baseProps, dispatch, rowId: "row-3" },
    });

    await waitFor(() => expect(result.current.highlightedRowId).toBe("row-3"));
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("locates only once", async () => {
    const dispatch = vi.fn();
    const { result, rerender } = renderHook((props: HookProps) => useDeepLinkedRow(props), {
      initialProps: { ...baseProps, dispatch },
    });

    await waitFor(() => expect(dispatch).toHaveBeenCalledTimes(1));
    rerender({ ...baseProps, dispatch, currentPage: 1 });
    rerender({ ...baseProps, dispatch, currentPage: 0 });
    expect(dispatch).toHaveBeenCalledTimes(1);
    expect(result.current.highlightedRowId).toBe("row-30");
  });

  it("clears the highlight via clearHighlight", async () => {
    const { result } = renderHook((props: HookProps) => useDeepLinkedRow(props), {
      initialProps: { ...baseProps, rowId: "row-3" },
    });

    await waitFor(() => expect(result.current.highlightedRowId).toBe("row-3"));
    act(() => result.current.clearHighlight());
    expect(result.current.highlightedRowId).toBeNull();
  });

  it("does nothing without a deep-linked row", () => {
    const dispatch = vi.fn();
    const { result } = renderHook((props: HookProps) => useDeepLinkedRow(props), {
      initialProps: { ...baseProps, dispatch, rowId: null },
    });

    expect(dispatch).not.toHaveBeenCalled();
    expect(result.current.highlightedRowId).toBeNull();
  });

  it("bails out when the row is not in this version", async () => {
    const dispatch = vi.fn();
    const { result } = renderHook((props: HookProps) => useDeepLinkedRow(props), {
      initialProps: { ...baseProps, dispatch, rowId: "not-there" },
    });

    await waitFor(() => expect(dispatch).not.toHaveBeenCalled());
    expect(result.current.highlightedRowId).toBeNull();
  });
});
