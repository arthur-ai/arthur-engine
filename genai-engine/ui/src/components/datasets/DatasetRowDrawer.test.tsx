import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DatasetRowDrawer } from "./DatasetRowDrawer";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

vi.mock("@/services/analytics", () => ({
  track: vi.fn(),
}));

const mocks = vi.hoisted(() => ({
  useDatasetRow: vi.fn(),
}));

vi.mock("@/hooks/useDatasetRow", () => ({
  useDatasetRow: mocks.useDatasetRow,
}));

const rowData: DatasetVersionRowResponse = {
  id: "row-1",
  data: [{ column_name: "input", column_value: "hello" }],
  created_at: 0,
};

const queryState = (overrides: object) => ({ data: undefined, isLoading: false, error: null, ...overrides });

function renderDrawer(props: Partial<React.ComponentProps<typeof DatasetRowDrawer>> = {}) {
  return render(<DatasetRowDrawer open onClose={vi.fn()} datasetId="ds-1" versionNumber={3} rowId="row-1" {...props} />);
}

describe("DatasetRowDrawer", () => {
  beforeEach(() => {
    mocks.useDatasetRow.mockReset();
  });

  afterEach(cleanup);

  it("shows a spinner while loading", () => {
    mocks.useDatasetRow.mockReturnValue(queryState({ isLoading: true }));
    renderDrawer();
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });

  it("shows a spinner while the version is still unknown", () => {
    mocks.useDatasetRow.mockReturnValue(queryState({}));
    renderDrawer({ versionNumber: undefined });
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });

  it("shows a friendly message for a 404", () => {
    mocks.useDatasetRow.mockReturnValue(queryState({ error: { isAxiosError: true, response: { status: 404 }, message: "Request failed" } }));
    renderDrawer();
    expect(screen.getByText("Row not found in this dataset version")).toBeTruthy();
  });

  it("shows the error message for other failures", () => {
    mocks.useDatasetRow.mockReturnValue(queryState({ error: new Error("boom") }));
    renderDrawer();
    expect(screen.getByText("boom")).toBeTruthy();
  });

  it("renders the row content on success", () => {
    mocks.useDatasetRow.mockReturnValue(queryState({ data: rowData }));
    renderDrawer();
    expect(screen.getByText("input")).toBeTruthy();
    expect(screen.getByText("hello")).toBeTruthy();
  });

  it("has an accessible close button", () => {
    mocks.useDatasetRow.mockReturnValue(queryState({ data: rowData }));
    renderDrawer();
    expect(screen.getByRole("button", { name: "Close" })).toBeTruthy();
  });

  it("keeps the content mounted while closing so the exit animation stays intact", () => {
    mocks.useDatasetRow.mockReturnValue(queryState({ data: rowData }));
    const { rerender } = renderDrawer();
    expect(screen.getByText("hello")).toBeTruthy();

    rerender(<DatasetRowDrawer open={false} onClose={vi.fn()} datasetId="ds-1" versionNumber={3} rowId={null} />);
    expect(screen.getByText("hello")).toBeTruthy();
  });
});
