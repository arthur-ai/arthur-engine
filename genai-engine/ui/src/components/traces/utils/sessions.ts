import { flattenSpans } from "./spans";

import { SessionTracesResponse } from "@/lib/api-client/api-client";
import { getCost, getTokens } from "@/utils/llm";

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
      total: 0,
      prompt: 0,
      completion: 0,
    },
  };

  for (const span of spans) {
    const tokens = getTokens(span);
    const cost = getCost(span);

    totals.token.total += tokens.total ?? 0;
    totals.token.prompt += tokens.input ?? 0;
    totals.token.completion += tokens.output ?? 0;

    totals.cost.total += cost.total ?? 0;
    totals.cost.prompt += cost.prompt ?? 0;
    totals.cost.completion += cost.completion ?? 0;
  }

  return totals;
}
