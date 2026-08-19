import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DatasetRowContent } from "./DatasetRowContent";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

vi.mock("@/services/analytics", () => ({
  track: vi.fn(),
}));

const rowData: DatasetVersionRowResponse = {
  id: "row-1",
  data: [
    { column_name: "input", column_value: "hello" },
    { column_name: "output", column_value: "world" },
  ],
  created_at: 0,
};

function renderContent(openInDatasetHref?: string) {
  return render(
    <MemoryRouter>
      <DatasetRowContent rowData={rowData} datasetId="ds-1" versionNumber={3} rowId="row-1" taskId="task-1" openInDatasetHref={openInDatasetHref} />
    </MemoryRouter>
  );
}

describe("DatasetRowContent", () => {
  afterEach(cleanup);

  it("renders the row id as a copyable chip", () => {
    renderContent();
    expect(screen.getByText("row-1")).toBeTruthy();
    expect(screen.getByTestId("ContentCopyIcon")).toBeTruthy();
  });

  it("renders one labeled block per column", () => {
    renderContent();
    expect(screen.getByText("input")).toBeTruthy();
    expect(screen.getByText("hello")).toBeTruthy();
    expect(screen.getByText("output")).toBeTruthy();
    expect(screen.getByText("world")).toBeTruthy();
  });

  it("renders the open-in-dataset link when a href is provided", () => {
    renderContent("/tasks/task-1/datasets/ds-1?version=3&row=row-1");
    const link = screen.getByRole("link", { name: "Open in dataset" });
    expect(link.getAttribute("href")).toBe("/tasks/task-1/datasets/ds-1?version=3&row=row-1");
  });

  it("renders no open-in-dataset link without a href", () => {
    renderContent();
    expect(screen.queryByRole("link", { name: "Open in dataset" })).toBeNull();
  });
});
