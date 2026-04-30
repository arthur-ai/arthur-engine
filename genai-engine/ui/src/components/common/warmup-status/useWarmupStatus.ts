import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ModelStatusResponse } from "@/lib/api-client/api-client";

export interface UseWarmupStatusOptions {
  /** Caller-provided async fetcher returning the warmup status payload. */
  fetcher: () => Promise<ModelStatusResponse>;
  /** Query key. Defaults to `["warmup-status"]` so the hook works standalone. */
  queryKey?: readonly unknown[];
  /** How often to poll while not yet ready. Defaults to 2000ms. */
  pollIntervalMs?: number;
  /** Whether the query is enabled. Defaults to true. */
  enabled?: boolean;
}

/**
 * Polls a warmup-status endpoint until `overall_status` becomes `"ready"`,
 * then stops. The poll interval honors the server-provided
 * `retry_after_seconds` hint when present, otherwise falls back to
 * `pollIntervalMs`.
 */
export function useWarmupStatus({
  fetcher,
  queryKey = ["warmup-status"],
  pollIntervalMs = 2000,
  enabled = true,
}: UseWarmupStatusOptions): UseQueryResult<ModelStatusResponse> {
  return useQuery({
    queryKey,
    queryFn: fetcher,
    enabled,
    staleTime: pollIntervalMs,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || data.overall_status === "ready") return false;
      const serverHint = data.retry_after_seconds;
      if (typeof serverHint === "number" && serverHint > 0) return serverHint * 1000;
      return pollIntervalMs;
    },
  });
}
