import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/hooks/useApi";

export function useDeleteTransformMutation(
  datasetId: string | undefined,
  onSuccess?: () => void
) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (transformId: string) => {
      if (!datasetId || !api) {
        throw new Error("Dataset ID or API client not available");
      }

      const response = await api.api.deleteTransformApiV2DatasetsDatasetIdTransformsTransformIdDelete(
        datasetId,
        transformId
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
