import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type { RagSearchSettingConfigurationRequest } from "@/lib/api-client/api-client";

interface CreateRagConfigParams {
  taskId: string;
  request: RagSearchSettingConfigurationRequest;
}

export function useCreateRagConfig() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ taskId, request }: CreateRagConfigParams) => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.createRagSearchSettings(taskId, request);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["rag-search-settings", variables.taskId] });
    },
  });
}

