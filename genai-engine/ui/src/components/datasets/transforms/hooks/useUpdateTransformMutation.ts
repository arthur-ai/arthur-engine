import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/hooks/useApi";
import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";

interface UpdateTransformParams {
  transformId: string;
  name: string;
  description: string;
  definition: TransformDefinition;
}

export function useUpdateTransformMutation(
  datasetId: string | undefined,
  onSuccess?: () => void
) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: UpdateTransformParams) => {
      if (!datasetId || !api) {
        throw new Error("Dataset ID or API client not available");
      }

      const response = await api.api.updateTransformApiV2DatasetsDatasetIdTransformsTransformIdPut(
        datasetId,
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
      if (datasetId) {
        queryClient.invalidateQueries({ queryKey: ["transforms", datasetId] });
      }
      onSuccess?.();
    },
  });
}
