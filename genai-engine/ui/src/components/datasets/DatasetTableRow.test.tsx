import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

let scrollSpy: ReturnType<typeof vi.fn>;

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
  beforeEach(() => {
    // jsdom has no scrollIntoView
    scrollSpy = vi.fn();
    Element.prototype.scrollIntoView = scrollSpy as unknown as Element["scrollIntoView"];
  });

  afterEach(cleanup);

  it("scrolls itself into view when highlighted", () => {
    renderRow({ isHighlighted: true });
    expect(scrollSpy).toHaveBeenCalledWith({ behavior: "smooth", block: "center" });
  });

  it("does not scroll when not highlighted", () => {
    renderRow();
    expect(scrollSpy).not.toHaveBeenCalled();
  });

  it("reports the end of its flash animation", () => {
    const onHighlightEnd = vi.fn();
    renderRow({ isHighlighted: true, onHighlightEnd });
    fireEvent(screen.getByRole("row"), new Event("animationend", { bubbles: true }));
    expect(onHighlightEnd).toHaveBeenCalledTimes(1);
  });

  it("ignores animation ends when not highlighted", () => {
    const onHighlightEnd = vi.fn();
    renderRow({ onHighlightEnd });
    fireEvent(screen.getByRole("row"), new Event("animationend", { bubbles: true }));
    expect(onHighlightEnd).not.toHaveBeenCalled();
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
