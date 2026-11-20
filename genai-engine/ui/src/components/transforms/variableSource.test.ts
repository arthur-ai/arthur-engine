import { describe, expect, it } from "vitest";

import { MIN_TRACE_MAX_CHARS, describeSpansRead, isWholeTrace, validateMaxChars } from "./variableSource";

import { buildTransformFromColumns, validateTransform } from "@/components/traces/components/add-to-dataset/utils/transformBuilder";

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
    expect(validateMaxChars("1999")).toContain(`at least ${MIN_TRACE_MAX_CHARS.toLocaleString()}`);
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

describe("buildTransformFromColumns", () => {
  it("keeps a whole-trace column as a trace variable and drops an unresolved span column", () => {
    expect(
      buildTransformFromColumns([
        {
          name: "trace",
          value: "TRACE v1 spans=4",
          path: "whole trace · 4 spans",
          span_name: "",
          attribute_path: "",
          source: "trace",
          max_chars: 5000,
        },
        { name: "unresolved", value: "", path: "", span_name: "", attribute_path: "" },
        { name: "search_output", value: "...", path: "search × 3, in trace order", span_name: "search", attribute_path: "attributes.output.value" },
      ])
    ).toEqual({
      variables: [
        { variable_name: "trace", source: "trace", span_name: "", attribute_path: "", max_chars: 5000, fallback: null },
        { variable_name: "search_output", span_name: "search", attribute_path: "attributes.output.value", max_chars: undefined, fallback: null },
      ],
    });
  });
});
