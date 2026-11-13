import { describe, expect, it } from "vitest";

import { completeTraceFilterRows, rowsToTraceFilter, traceFilterSchema, traceFilterToRows, type TraceFilterRow } from "./traceFilter";

const paid: TraceFilterRow = { spanName: "", attributePath: "attributes.metadata.plan", operator: "equals", value: "paid" };

describe("trace filter", () => {
  it("sends no filter when there are no conditions", () => {
    expect(rowsToTraceFilter([])).toBeNull();
  });

  it("sends an empty span name as any span and drops the value for exists", () => {
    expect(rowsToTraceFilter([paid, { spanName: "llm", attributePath: "attributes.llm.model_name", operator: "exists", value: "x" }])).toEqual([
      { span_name: null, attribute_path: "attributes.metadata.plan", operator: "equals", value: "paid" },
      { span_name: "llm", attribute_path: "attributes.llm.model_name", operator: "exists", value: null },
    ]);
  });

  it("round-trips a saved filter into form rows", () => {
    expect(traceFilterToRows(rowsToTraceFilter([paid]))).toEqual([paid]);
    expect(traceFilterToRows(null)).toEqual([]);
  });

  it("requires a path, and a value unless the operator is exists", () => {
    expect(traceFilterSchema.safeParse([paid]).success).toBe(true);
    expect(traceFilterSchema.safeParse([{ ...paid, attributePath: " " }]).success).toBe(false);
    expect(traceFilterSchema.safeParse([{ ...paid, value: "" }]).success).toBe(false);
    expect(traceFilterSchema.safeParse([{ ...paid, operator: "exists", value: "" }]).success).toBe(true);
  });

  it("keeps the complete rows when another row is still being filled in", () => {
    const blank: TraceFilterRow = { spanName: "", attributePath: "", operator: "equals", value: "" };
    expect(completeTraceFilterRows([paid, blank])).toEqual([paid]);
    expect(completeTraceFilterRows([blank])).toEqual([]);
  });
});
