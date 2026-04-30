import type { UseQueryResult } from "@tanstack/react-query";

import { useWarmupStatus } from "@/components/common/warmup-status";
import { useApi } from "@/hooks/useApi";
import type { ModelStatusResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

/**
 * App-side adapter that wires the portable `useWarmupStatus` hook to this
 * app's authenticated API client.
 */
export function useEngineWarmupStatus(): UseQueryResult<ModelStatusResponse> {
  const api = useApi();

  return useWarmupStatus({
    queryKey: queryKeys.system.warmupStatus(),
    enabled: api !== null,
    fetcher: async () => {
      const response = await api!.api.getModelStatusApiV2SystemModelStatusGet();
      return response.data;
    },
  });
}
