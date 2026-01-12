import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type { RagSearchSettingConfigurationUpdateRequest } from "@/lib/api-client/api-client";

interface UpdateRagConfigParams {
  configId: string;
  request: RagSearchSettingConfigurationUpdateRequest;
}

export function useUpdateRagConfig() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ configId, request }: UpdateRagConfigParams) => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.updateRagSearchSettingsApiV1RagSearchSettingsSettingConfigurationIdPatch(configId, request);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["rag-config-versions", variables.configId] });
      queryClient.invalidateQueries({ queryKey: ["rag-search-settings"] });
    },
  });
}
