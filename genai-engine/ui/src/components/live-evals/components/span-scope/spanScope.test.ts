import { describe, expect, it } from "vitest";

import { defaultSpanScope, spanFilterJson, spanScopeFromEval, spanScopeSchema, spanScopeToRequest } from "./spanScope";

describe("span scope form values", () => {
  it("leaves trace scope as it was: no span filter, no rollup rule", () => {
    expect(spanScopeToRequest(defaultSpanScope())).toEqual({ scope: "trace", span_filter: null, rollup_rule: null, max_spans_per_trace: 20 });
    expect(spanScopeSchema.safeParse(defaultSpanScope()).success).toBe(true);
  });

  it("requires a span name or kind and an explicit rollup rule in span scope", () => {
    const result = spanScopeSchema.safeParse({ ...defaultSpanScope(), scope: "span" });
    expect(result.success).toBe(false);
    expect(result.error?.issues.map((issue) => issue.path.join("."))).toEqual(["spanName", "rollupRule"]);
    expect(spanScopeSchema.safeParse({ ...defaultSpanScope(), scope: "span", spanKind: "TOOL", rollupRule: "final_attempt" }).success).toBe(true);
    expect(spanScopeSchema.safeParse({ ...defaultSpanScope(), scope: "span", spanKind: "TOOL", rollupRule: "any_fail", maxSpans: "0" }).success).toBe(
      false
    );
  });

  it("round-trips an eval's span settings", () => {
    const values = { scope: "span" as const, spanName: "lookup_order", spanKind: "", rollupRule: "final_attempt" as const, maxSpans: "5" };
    const request = spanScopeToRequest(values);
    expect(request).toEqual({
      scope: "span",
      span_filter: { span_name: "lookup_order", span_kind: null, conditions: [] },
      rollup_rule: "final_attempt",
      max_spans_per_trace: 5,
    });
    expect(spanScopeFromEval(request)).toEqual(values);
    expect(spanFilterJson(values)).toBe('{"span_name":"lookup_order","span_kind":null,"conditions":[]}');
    expect(spanFilterJson({ ...values, spanName: "" })).toBeNull();
  });
});
