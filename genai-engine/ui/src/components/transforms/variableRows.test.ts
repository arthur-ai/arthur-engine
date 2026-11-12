import { describe, expect, it } from "vitest";

import { describeVariableSpans, emptyVariableRow, rowToVariable, validateVariableRow, variableToRow, wholeTraceVariableNames } from "./variableRows";

describe("transform variable rows", () => {
  it("round-trips span kind and selector, with empty strings as null", () => {
    const row = { ...emptyVariableRow("result"), span_kind: "TOOL", span_selector: "last" as const, attribute_path: "attributes.output.value" };
    const variable = rowToVariable(row);
    expect(variable).toMatchObject({ span_name: null, span_kind: "TOOL", span_selector: "last" });
    expect(variableToRow(variable)).toEqual(row);
  });

  it("needs a span name or kind, except for the judged span", () => {
    const row = { ...emptyVariableRow("result"), attribute_path: "a" };
    expect(validateVariableRow(row, 0)).toEqual(["Variable 1: Span name or span kind is required"]);
    expect(validateVariableRow({ ...row, span_kind: "TOOL" }, 0)).toEqual([]);
    expect(validateVariableRow({ ...row, span_selector: "current" }, 0)).toEqual([]);
  });

  it("describes which spans a variable reads", () => {
    expect(describeVariableSpans({ variable_name: "v", span_name: "lookup_order", attribute_path: "a" })).toBe("lookup_order");
    expect(describeVariableSpans({ variable_name: "v", span_kind: "TOOL", span_selector: "all", attribute_path: "a" })).toBe(
      "any TOOL span, all matches"
    );
    expect(describeVariableSpans({ variable_name: "v", span_selector: "current", attribute_path: "a" })).toBe("the judged span");
  });

  it("sends a whole-trace variable with an empty path and its size budget", () => {
    const row = { ...emptyVariableRow("conversation"), source: "trace" as const, max_chars: "20000" };
    const variable = rowToVariable(row);
    expect(variable).toEqual({ variable_name: "conversation", source: "trace", max_chars: 20000, attribute_path: "", fallback: undefined });
    expect(variableToRow(variable)).toMatchObject({ source: "trace", max_chars: "20000" });
    expect(validateVariableRow(row, 0)).toEqual([]);
    expect(validateVariableRow({ ...row, max_chars: "500" }, 1)).toEqual([
      "Variable 2: Size budget must be a whole number of at least 2000 characters",
    ]);
    expect(rowToVariable({ ...row, max_chars: "" }).max_chars).toBeNull();
    expect(describeVariableSpans(variable)).toBe(`the whole trace, up to ${(20000).toLocaleString()} chars`);
  });

  it("finds the variables that read the whole trace", () => {
    expect(
      wholeTraceVariableNames([
        { variable_name: "conversation", source: "trace", attribute_path: "" },
        { variable_name: "tool_output", span_kind: "TOOL", attribute_path: "a" },
      ])
    ).toEqual(["conversation"]);
    expect(wholeTraceVariableNames(undefined)).toEqual([]);
  });
});
