import { describe, expect, it } from "vitest";

import { describeSpansRead, isWholeTrace, validateMaxChars } from "./variableSource";

import { validateTransform } from "@/components/traces/components/add-to-dataset/utils/transformBuilder";

const search = { source: "span" as const, span_name: "search", attribute_path: "attributes.output.value" };
const wholeTrace = { source: "trace" as const, span_name: "", attribute_path: "" };

describe("describeSpansRead", () => {
  it("names the span and path for a single match", () => {
    expect(describeSpansRead(search, ["search-1"])).toBe("search.attributes.output.value");
  });

  it("counts every match of a retried call", () => {
    expect(describeSpansRead(search, ["search-1", "search-2", "search-3"])).toBe("search × 3, in trace order");
  });

  it("says nothing when no span matched", () => {
    expect(describeSpansRead(search, [])).toBe("");
  });

  it("counts every span for the whole trace", () => {
    expect(describeSpansRead(wholeTrace, ["root", "search-1", "search-2", "search-3"])).toBe("whole trace · 4 spans");
  });
});

describe("isWholeTrace", () => {
  it("treats a missing source as a span variable", () => {
    expect(isWholeTrace({})).toBe(false);
    expect(isWholeTrace(wholeTrace)).toBe(true);
  });
});

describe("validateMaxChars", () => {
  it("accepts empty (the default) and values at the floor", () => {
    expect(validateMaxChars("")).toBeNull();
    expect(validateMaxChars("2000")).toBeNull();
    expect(validateMaxChars("48000")).toBeNull();
  });

  it("rejects values under the floor and non-integers", () => {
    expect(validateMaxChars("1999")).toMatch(/at least 2,000/);
    expect(validateMaxChars("5000.5")).toMatch(/whole number/);
    expect(validateMaxChars("lots")).toMatch(/whole number/);
  });
});

describe("validateTransform", () => {
  it("needs no span name or attribute path for a whole-trace variable", () => {
    expect(validateTransform({ variables: [{ variable_name: "trace", ...wholeTrace }] })).toEqual([]);
  });

  it("still needs them for a span variable", () => {
    expect(validateTransform({ variables: [{ variable_name: "x", source: "span", span_name: "", attribute_path: "" }] })).toEqual([
      "Variable x: span_name is required",
      "Variable x: attribute_path is required",
    ]);
  });

  it("checks the size budget floor for a span variable too", () => {
    expect(validateTransform({ variables: [{ variable_name: "x", ...search, max_chars: 500 }] })).toEqual([
      "Variable x: max_chars must be at least 2000",
    ]);
  });

  it("checks the whole-trace size budget floor", () => {
    expect(validateTransform({ variables: [{ variable_name: "trace", ...wholeTrace, max_chars: 1000 }] })).toEqual([
      "Variable trace: max_chars must be at least 2000",
    ]);
  });
});
