import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";

export function useDeleteTransformMutation(
  taskId: string | undefined,
  onSuccess?: () => void
) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (transformId: string) => {
      if (!taskId || !api) {
        throw new Error("Task ID or API client not available");
      }

      const response = await api.api.deleteTransformApiV1TracesTransformsTransformIdDelete(
        transformId
      );

      return response.data;
    },
    onSuccess: () => {
      if (taskId) {
        queryClient.invalidateQueries({ queryKey: ["transforms", taskId] });
      }
      onSuccess?.();
    },
  });
}
