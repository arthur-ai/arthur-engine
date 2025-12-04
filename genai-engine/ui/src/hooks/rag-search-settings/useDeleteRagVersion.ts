import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";

interface DeleteRagVersionParams {
  configId: string;
  versionNumber: number;
}

export function useDeleteRagVersion() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ configId, versionNumber }: DeleteRagVersionParams) => {
      if (!api) {
        throw new Error("API client not available");
      }

      await api.api.deleteRagSearchSettingVersion(configId, versionNumber);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["rag-config-versions", variables.configId] });
      queryClient.invalidateQueries({ queryKey: ["rag-search-settings"] });
    },
  });
}

