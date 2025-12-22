import { useMutation, useQueryClient } from "@tanstack/react-query";

import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";
import { useApi } from "@/hooks/useApi";

interface UpdateTransformParams {
  transformId: string;
  name: string;
  description: string;
  definition: TransformDefinition;
}

export function useUpdateTransformMutation(
  taskId: string | undefined,
  onSuccess?: () => void
) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: UpdateTransformParams) => {
      if (!taskId || !api) {
        throw new Error("Task ID or API client not available");
      }

      const response = await api.api.updateTransformApiV1TracesTransformsTransformIdPatch(
        params.transformId,
        {
          name: params.name,
          description: params.description || null,
          definition: params.definition,
        }
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
