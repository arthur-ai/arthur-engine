import { getCost, getTokens } from "@arthur/shared-components";
import { flattenSpans } from "@arthur/shared-components/traces";

import { SessionTracesResponse } from "@/lib/api-client/api-client";

// Sums that stay null when nothing was reported, so an unknown cost isn't shown as free.
const addReported = (sum: number | null, value: number | null | undefined) => (value == null ? sum : (sum ?? 0) + value);

export function getSessionTotals(session: SessionTracesResponse) {
  const traces = session.traces;
  const spans = flattenSpans(traces.flatMap((trace) => trace.root_spans ?? []));

  const totals = {
    token: {
      total: 0,
      prompt: 0,
      completion: 0,
    },
    cost: {
      total: null as number | null,
      prompt: null as number | null,
      completion: null as number | null,
      unpricedSpanCount: null as number | null,
    },
  };

  for (const span of spans) {
    const tokens = getTokens(span);
    const cost = getCost(span);

    totals.token.total += tokens.total ?? 0;
    totals.token.prompt += tokens.input ?? 0;
    totals.token.completion += tokens.output ?? 0;

    totals.cost.total = addReported(totals.cost.total, cost.total);
    totals.cost.prompt = addReported(totals.cost.prompt, cost.prompt);
    totals.cost.completion = addReported(totals.cost.completion, cost.completion);
    totals.cost.unpricedSpanCount = addReported(totals.cost.unpricedSpanCount, span.unpriced_span_count);
  }

  return totals;
}
