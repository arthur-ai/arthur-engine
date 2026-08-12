import { describe, expect, it } from "vitest";

import { mergeVersionIntoParams } from "./versionSearchParams";

describe("mergeVersionIntoParams", () => {
  it("sets the version while preserving the row deep link", () => {
    const prev = new URLSearchParams("row=abc-123");
    const next = mergeVersionIntoParams(prev, 4);
    expect(next.get("version")).toBe("4");
    expect(next.get("row")).toBe("abc-123");
  });

  it("replaces an existing version", () => {
    const prev = new URLSearchParams("version=2&row=abc-123");
    const next = mergeVersionIntoParams(prev, 7);
    expect(next.get("version")).toBe("7");
    expect(next.get("row")).toBe("abc-123");
  });

  it("deletes the version when none is selected, keeping other params", () => {
    const prev = new URLSearchParams("version=2&row=abc-123");
    const next = mergeVersionIntoParams(prev, undefined);
    expect(next.get("version")).toBeNull();
    expect(next.get("row")).toBe("abc-123");
  });

  it("does not mutate the previous params", () => {
    const prev = new URLSearchParams("version=2");
    mergeVersionIntoParams(prev, 9);
    expect(prev.get("version")).toBe("2");
  });
});
