import { useApiQuery } from "./useApiQuery";

import type { SpanWithMetricsResponse } from "@/lib/api-client/api-client";

/**
 * Hook to fetch a span by ID using TanStack Query.
 * Automatically refetches when spanId changes.
 */
export function useSpan(spanId: string | undefined) {
  const { data, error, isLoading } = useApiQuery<"getSpanByIdApiV1TracesSpansSpanIdGet">({
    method: "getSpanByIdApiV1TracesSpansSpanIdGet",
    args: [spanId!] as const,
    enabled: !!spanId,
    queryOptions: {
      staleTime: 30000,
    },
  });

  return {
    span: data as SpanWithMetricsResponse | undefined,
    error,
    isLoading,
  };
}
