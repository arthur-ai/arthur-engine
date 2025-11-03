import { SessionTracesResponse } from "@/lib/api-client/api-client";
import { flattenSpans } from "./spans";
import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { getInputTokens, getOutputTokens, getTotalTokens } from "@/utils/llm";

export function getSessionTotals(session: SessionTracesResponse) {
  const traces = session.traces;
  const spans = flattenSpans(traces.flatMap((trace) => trace.root_spans ?? []));

  const totals = {
    [SemanticConventions.LLM_TOKEN_COUNT_TOTAL]: 0,
    [SemanticConventions.LLM_TOKEN_COUNT_PROMPT]: 0,
    [SemanticConventions.LLM_TOKEN_COUNT_COMPLETION]: 0,
  };

  for (const span of spans) {
    totals[SemanticConventions.LLM_TOKEN_COUNT_TOTAL] += getTotalTokens(span);
    totals[SemanticConventions.LLM_TOKEN_COUNT_PROMPT] += getInputTokens(span);
    totals[SemanticConventions.LLM_TOKEN_COUNT_COMPLETION] +=
      getOutputTokens(span);
  }

  return totals;
}
