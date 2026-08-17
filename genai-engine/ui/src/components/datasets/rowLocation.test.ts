import { describe, expect, it } from "vitest";

import { computeRowPage } from "./rowLocation";

const ids = Array.from({ length: 60 }, (_, i) => `row-${i}`);

describe("computeRowPage", () => {
  it("returns page 0 for rows on the first page", () => {
    expect(computeRowPage(ids, "row-0", 25)).toBe(0);
    expect(computeRowPage(ids, "row-24", 25)).toBe(0);
  });

  it("crosses page boundaries correctly", () => {
    expect(computeRowPage(ids, "row-25", 25)).toBe(1);
    expect(computeRowPage(ids, "row-49", 25)).toBe(1);
    expect(computeRowPage(ids, "row-50", 25)).toBe(2);
  });

  it("handles other page sizes", () => {
    expect(computeRowPage(ids, "row-9", 10)).toBe(0);
    expect(computeRowPage(ids, "row-10", 10)).toBe(1);
    expect(computeRowPage(ids, "row-59", 100)).toBe(0);
  });

  it("returns null when the row is missing", () => {
    expect(computeRowPage(ids, "not-there", 25)).toBeNull();
  });

  it("returns null for an empty list", () => {
    expect(computeRowPage([], "row-0", 25)).toBeNull();
  });

  it("returns null for a non-positive page size", () => {
    expect(computeRowPage(ids, "row-0", 0)).toBeNull();
  });
});
