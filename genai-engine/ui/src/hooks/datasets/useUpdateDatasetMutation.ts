import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";
import { DatasetFormData } from "@/types/dataset";

export interface UseUpdateDatasetMutationReturn {
  mutateAsync: (data: DatasetFormData & { id: string }) => Promise<void>;
  isPending: boolean;
}

export function useUpdateDatasetMutation(
  onSuccess: () => void
): UseUpdateDatasetMutationReturn {
  const api = useApi();

  const { mutateAsync, isPending } = useApiMutation({
    mutationFn: async (data: DatasetFormData & { id: string }) => {
      if (!api) throw new Error("API not available");

      return api.api.updateDatasetApiV2DatasetsDatasetIdPatch(data.id, {
        name: data.name,
        description: data.description || null,
        metadata: data.metadata || null,
      });
    },
    invalidateQueries: [{ queryKey: queryKeys.datasets.search.all() }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to update dataset:", err);
    },
  });

  return {
    mutateAsync: async (data: DatasetFormData & { id: string }) => {
      await mutateAsync(data);
    },
    isPending,
  };
}
