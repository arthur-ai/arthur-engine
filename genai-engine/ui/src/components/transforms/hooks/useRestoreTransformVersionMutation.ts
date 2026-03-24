import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";

export function useRestoreTransformVersionMutation(transformId: string, onSuccess?: () => void) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (versionId: string) => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.restoreTransformVersionApiV1TracesTransformsTransformIdVersionsVersionIdRestorePost(transformId, versionId);

      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transformVersions", transformId] });
      queryClient.invalidateQueries({ queryKey: ["transform", transformId] });
      queryClient.invalidateQueries({ queryKey: ["transforms"] });
      onSuccess?.();
    },
  });
}
