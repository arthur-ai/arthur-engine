import { Table, TableBody, TableCell } from "@mui/material";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ExpandableTableRow } from "./ExpandableTableRow";

const renderRow = (props: Partial<React.ComponentProps<typeof ExpandableTableRow>> = {}) =>
  render(
    <Table>
      <TableBody>
        <ExpandableTableRow colSpan={2} detail={<div>Detail content</div>} {...props}>
          <TableCell>Visible cell</TableCell>
        </ExpandableTableRow>
      </TableBody>
    </Table>
  );

describe("ExpandableTableRow", () => {
  afterEach(cleanup);

  it("hides the detail content until the row is expanded", () => {
    renderRow();

    expect(screen.getByText("Visible cell")).toBeTruthy();
    expect(screen.queryByText("Detail content")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Expand row" }));

    expect(screen.getByText("Detail content")).toBeTruthy();
  });

  it("marks the toggle as expanded after clicking it", () => {
    renderRow();

    fireEvent.click(screen.getByRole("button", { name: "Expand row" }));

    expect(screen.getByRole("button", { name: "Collapse row" }).getAttribute("aria-expanded")).toBe("true");
  });

  it("renders no toggle when expanding is disabled", () => {
    renderRow({ expandDisabled: true });

    expect(screen.queryByRole("button")).toBeNull();
  });
});
