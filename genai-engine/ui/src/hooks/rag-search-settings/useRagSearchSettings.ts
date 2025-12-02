import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";

interface UseRagSearchSettingsParams {
  config_name?: string;
  page?: number;
  page_size?: number;
}

export function useRagSearchSettings(taskId: string | undefined, params?: UseRagSearchSettingsParams) {
  const api = useApi();

  return useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: ["rag-search-settings", taskId, params],
    queryFn: async () => {
      if (!api || !taskId) {
        throw new Error("API client or task ID not available");
      }

      const response = await api.api.getTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGet({
        taskId,
        ...params,
      });

      return response.data;
    },
    enabled: !!taskId && !!api,
  });
}
