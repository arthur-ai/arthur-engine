import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import dayjs from "dayjs";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

export function getSpanInput(span?: NestedSpanWithMetricsResponse) {
  return span?.raw_data.attributes?.[SemanticConventions.INPUT_VALUE] || null;
}

export function getSpanOutput(span?: NestedSpanWithMetricsResponse) {
  return span?.raw_data.attributes?.[SemanticConventions.OUTPUT_VALUE] || null;
}

export function getSpanDuration(span?: NestedSpanWithMetricsResponse) {
  return span?.start_time && span?.end_time
    ? dayjs(span.end_time).diff(dayjs(span.start_time), "ms")
    : null;
}

export function flattenSpans(
  rootSpans: NestedSpanWithMetricsResponse[]
): NestedSpanWithMetricsResponse[] {
  const result: NestedSpanWithMetricsResponse[] = [];

  function flattenRecursive(spans: NestedSpanWithMetricsResponse[]) {
    for (const span of spans) {
      result.push(span);
      if (span.children && span.children.length > 0) {
        flattenRecursive(span.children);
      }
    }
  }

  flattenRecursive(rootSpans);
  return result;
}

export function getSpanModel(span?: NestedSpanWithMetricsResponse) {
  return (
    span?.raw_data.attributes?.[SemanticConventions.LLM_MODEL_NAME] || null
  );
}

export function getSpanCost(span?: NestedSpanWithMetricsResponse) {
  return Number(span?.raw_data.attributes?.[SemanticConventions.LLM_COST]) || 0;
}
