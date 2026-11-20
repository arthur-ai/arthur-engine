import { NestedSpanWithMetricsResponse, TransformExtractionResponseList } from "@/lib/api-client/api-client";

/**
 * Name of the span a variable's previewed value was read from, as the engine
 * reported it, or undefined when no span supplied a value. The engine decides
 * which span a variable reads (span selector, span kind, tree order), so the
 * preview takes its answer instead of matching spans again here.
 */
export const previewSourceSpanName = (
  variableName: string,
  executionResult: TransformExtractionResponseList,
  flatSpans: NestedSpanWithMetricsResponse[]
): string | undefined => {
  const spanIds = executionResult.variable_spans?.find((v) => v.variable_name === variableName)?.span_ids ?? [];
  if (!spanIds.length) return undefined;
  const span = flatSpans.find((s) => s.span_id === spanIds[0]);
  return span?.span_name ?? undefined;
};
