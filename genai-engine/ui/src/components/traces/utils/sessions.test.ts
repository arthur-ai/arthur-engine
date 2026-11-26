import { describe, expect, it } from "vitest";

import { getSessionTotals } from "./sessions";

import type { NestedSpanWithMetricsResponse, SessionTracesResponse } from "@/lib/api-client/api-client";

const llmSpan = (overrides: Partial<NestedSpanWithMetricsResponse>) =>
  ({ span_kind: "LLM", children: [], raw_data: {}, ...overrides }) as unknown as NestedSpanWithMetricsResponse;

const session = (...spans: NestedSpanWithMetricsResponse[]) =>
  ({ session_id: "s", count: 1, traces: [{ trace_id: "t", root_spans: spans }] }) as unknown as SessionTracesResponse;

describe("getSessionTotals", () => {
  it("adds up costs and the LLM spans that couldn't be priced", () => {
    const { cost } = getSessionTotals(
      session(
        llmSpan({ prompt_token_cost: 0.01, completion_token_cost: 0.02, total_token_cost: 0.03, unpriced_span_count: 0 }),
        llmSpan({ unpriced_span_count: 1 })
      )
    );

    expect(cost.total).toBeCloseTo(0.03);
    expect(cost.unpricedSpanCount).toBe(1);
  });

  it("keeps an unreported cost unknown instead of zero", () => {
    const { cost } = getSessionTotals(session(llmSpan({ unpriced_span_count: 1 })));

    expect(cost.total).toBeNull();
  });
});
