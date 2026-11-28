import { describe, expect, it } from "vitest";

import { previewSourceSpanName } from "./previewSources";

import { NestedSpanWithMetricsResponse, TransformExtractionResponseList } from "@/lib/api-client/api-client";

const span = (span_id: string, span_name: string) => ({ span_id, span_name }) as NestedSpanWithMetricsResponse;

// A retried tool call: the first lookup_order failed, the second succeeded.
const flatSpans = [span("root", "agent"), span("call-1", "lookup_order"), span("call-2", "lookup_order"), span("t3", "refund_order")];

const result = (variable_spans: TransformExtractionResponseList["variable_spans"]): TransformExtractionResponseList => ({
  variables: [],
  missing_spans: [],
  missing_variables: [],
  variable_spans,
});

describe("previewSourceSpanName", () => {
  it("uses the span the engine read, not the first span with the name", () => {
    const executed = result([{ variable_name: "retried", span_ids: ["call-2"] }]);
    expect(previewSourceSpanName("retried", executed, flatSpans)).toBe("lookup_order");
  });

  it("names the span for a span-kind-only variable, which has no span name of its own", () => {
    const executed = result([{ variable_name: "tool_output", span_ids: ["t3"] }]);
    expect(previewSourceSpanName("tool_output", executed, flatSpans)).toBe("refund_order");
  });

  it("returns undefined when no span supplied a value", () => {
    const executed = result([{ variable_name: "missing", span_ids: [] }]);
    expect(previewSourceSpanName("missing", executed, flatSpans)).toBeUndefined();
    expect(previewSourceSpanName("unknown", executed, flatSpans)).toBeUndefined();
  });
});
