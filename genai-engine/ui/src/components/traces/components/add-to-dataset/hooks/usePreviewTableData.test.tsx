import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TracesTable } from "../../TracesTable";

import { usePreviewTableData } from "./usePreviewTableData";

const Preview = () => {
  const { table } = usePreviewTableData([
    { name: "question", value: "How much did it cost?" },
    { name: "answer", value: "Very little" },
  ] as Parameters<typeof usePreviewTableData>[0]);

  return <TracesTable table={table} loading={false} />;
};

describe("usePreviewTableData", () => {
  it("renders one row of the extracted values under their column names", () => {
    render(<Preview />);

    expect(screen.getByRole("columnheader", { name: "question" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "answer" })).toBeTruthy();
    expect(screen.getByRole("cell", { name: "How much did it cost?" })).toBeTruthy();
    expect(screen.getByRole("cell", { name: "Very little" })).toBeTruthy();
  });

  it("doesn't offer sorting on a single preview row", () => {
    render(<Preview />);

    for (const sortLabel of screen.getAllByRole("button")) {
      expect(sortLabel.getAttribute("aria-disabled")).toBe("true");
    }
  });
});
