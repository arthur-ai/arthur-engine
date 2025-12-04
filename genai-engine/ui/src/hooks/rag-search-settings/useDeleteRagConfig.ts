import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";

export function useDeleteRagConfig() {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (configId: string) => {
      if (!api) {
        throw new Error("API client not available");
      }

      await api.api.deleteRagSearchSetting(configId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rag-search-settings"] });
    },
  });
}

