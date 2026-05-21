import { describe, expect, it } from "vitest";

import { getTaskIdFromPathname } from "./getTaskIdFromPathname";

describe("getTaskIdFromPathname", () => {
  it("extracts task id from task routes", () => {
    expect(getTaskIdFromPathname("/tasks/abc-123/overview")).toBe("abc-123");
    expect(getTaskIdFromPathname("/tasks/abc-123/evaluate")).toBe("abc-123");
  });

  it("returns undefined for non-task routes", () => {
    expect(getTaskIdFromPathname("/")).toBeUndefined();
    expect(getTaskIdFromPathname("/tasks/%3AtaskId/overview")).toBeUndefined();
  });
});
