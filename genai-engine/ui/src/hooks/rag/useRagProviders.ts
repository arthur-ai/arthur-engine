import { useQuery, UseQueryResult } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type { RagProviderConfigurationResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

interface UseRagProvidersResult {
  providers: RagProviderConfigurationResponse[];
  count: number;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

interface RagProvidersResponse {
  rag_provider_configurations: RagProviderConfigurationResponse[];
  count: number;
}

export function useRagProviders(taskId: string | undefined): UseRagProvidersResult {
  const api = useApi();

  const queryResult: UseQueryResult<RagProvidersResponse, Error> = useQuery<RagProvidersResponse, Error>({
    queryKey: queryKeys.ragProviders.list(taskId || ""),
    queryFn: async () => {
      if (!taskId || !api) {
        throw new Error("Task ID or API not available");
      }

      const response = await api.api.getRagProvidersApiV1TasksTaskIdRagProvidersGet({
        taskId,
        page: 0,
        page_size: 100,
      });

      return response.data;
    },
    enabled: !!taskId && !!api,
  });

  return {
    providers: queryResult.data?.rag_provider_configurations || [],
    count: queryResult.data?.count || 0,
    isLoading: queryResult.isLoading,
    error: queryResult.error,
    refetch: queryResult.refetch,
  };
}
