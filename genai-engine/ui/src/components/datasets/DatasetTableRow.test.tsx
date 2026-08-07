import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DatasetTableRow } from "./DatasetTableRow";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

vi.mock("@/services/analytics", () => ({
  track: vi.fn(),
}));

const row: DatasetVersionRowResponse = {
  id: "row-1",
  data: [{ column_name: "input", column_value: "hello" }],
  created_at: 0,
};

function renderRow(props: Partial<React.ComponentProps<typeof DatasetTableRow>> = {}) {
  return render(
    <table>
      <tbody>
        <DatasetTableRow row={row} columns={["input"]} onEdit={vi.fn()} onDelete={vi.fn()} datasetId="ds-1" {...props} />
      </tbody>
    </table>
  );
}

describe("DatasetTableRow", () => {
  afterEach(cleanup);

  it("exposes the row id on the DOM for scroll targeting", () => {
    renderRow();
    expect(screen.getByRole("row").getAttribute("data-row-id")).toBe("row-1");
  });

  it("renders a view button that reports the row id", () => {
    const onView = vi.fn();
    renderRow({ onView });
    fireEvent.click(screen.getByRole("button", { name: "View row" }));
    expect(onView).toHaveBeenCalledWith("row-1");
  });

  it("renders no view button without an onView handler", () => {
    renderRow();
    expect(screen.queryByRole("button", { name: "View row" })).toBeNull();
  });

  it("keeps edit and delete actions working", () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    renderRow({ onEdit, onDelete });

    fireEvent.click(screen.getByTestId("EditIcon").closest("button")!);
    expect(onEdit).toHaveBeenCalledWith(row);

    fireEvent.click(screen.getByTestId("DeleteIcon").closest("button")!);
    expect(onDelete).toHaveBeenCalledWith("row-1");
  });
});
