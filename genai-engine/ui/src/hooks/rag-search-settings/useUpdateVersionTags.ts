import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";

interface UpdateVersionTagsParams {
  configId: string;
  versionNumber: number;
  tags: string[];
}

export function useUpdateVersionTags() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ configId, versionNumber, tags }: UpdateVersionTagsParams) => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.updateRagSearchSettingsVersionApiV1RagSearchSettingsSettingConfigurationIdVersionsVersionNumberPatch(
        configId,
        versionNumber,
        { tags }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["rag-config-versions", variables.configId] });
      queryClient.invalidateQueries({ queryKey: ["rag-search-settings"] });
    },
  });
}

