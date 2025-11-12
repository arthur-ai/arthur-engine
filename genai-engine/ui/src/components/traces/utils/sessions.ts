import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";

import { flattenSpans } from "./spans";

import { SessionTracesResponse } from "@/lib/api-client/api-client";
import { getTokens } from "@/utils/llm";

export function getSessionTotals(session: SessionTracesResponse) {
  const traces = session.traces;
  const spans = flattenSpans(traces.flatMap((trace) => trace.root_spans ?? []));

  const totals = {
    [SemanticConventions.LLM_TOKEN_COUNT_TOTAL]: 0,
    [SemanticConventions.LLM_TOKEN_COUNT_PROMPT]: 0,
    [SemanticConventions.LLM_TOKEN_COUNT_COMPLETION]: 0,
  };

  for (const span of spans) {
    const tokens = getTokens(span);

    totals[SemanticConventions.LLM_TOKEN_COUNT_TOTAL] += tokens.total ?? 0;
    totals[SemanticConventions.LLM_TOKEN_COUNT_PROMPT] += tokens.input ?? 0;
    totals[SemanticConventions.LLM_TOKEN_COUNT_COMPLETION] += tokens.output ?? 0;
  }

  return totals;
}
