import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type { RagSearchSettingConfigurationNewVersionRequest } from "@/lib/api-client/api-client";

interface CreateRagVersionParams {
  configId: string;
  request: RagSearchSettingConfigurationNewVersionRequest;
}

export function useCreateRagVersion() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ configId, request }: CreateRagVersionParams) => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.createRagSearchSettingsVersion(configId, request);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["rag-config-versions", variables.configId] });
      queryClient.invalidateQueries({ queryKey: ["rag-search-settings"] });
    },
  });
}

