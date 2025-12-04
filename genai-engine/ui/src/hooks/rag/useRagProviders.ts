import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

export function useRagProviders(taskId?: string) {
  const api = useApi();

  const { data, isLoading, error, refetch } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.ragProviders.list(taskId || ""),
    enabled: Boolean(taskId && api),
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
  });

  return {
    providers: data?.rag_provider_configurations ?? [],
    count: data?.count ?? 0,
    isLoading,
    error: error ?? null,
    refetch,
  };
}
