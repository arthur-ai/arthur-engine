import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/hooks/useApi";
import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";

interface CreateTransformParams {
  name: string;
  description: string;
  definition: TransformDefinition;
}

export function useCreateTransformMutation(
  datasetId: string | undefined,
  onSuccess?: () => void
) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: CreateTransformParams) => {
      if (!datasetId || !api) {
        throw new Error("Dataset ID or API client not available");
      }

      const response = await api.api.createTransformApiV2DatasetsDatasetIdTransformsPost(
        datasetId,
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
