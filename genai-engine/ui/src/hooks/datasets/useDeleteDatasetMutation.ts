import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";
import { deleteDataset } from "@/services/datasetService";

export const useDeleteDatasetMutation = () => {
  const api = useApi();

  return useApiMutation<void, string>({
    mutationFn: async (datasetId: string) => {
      if (!api) throw new Error("API not available");
      return deleteDataset(api, datasetId);
    },
    invalidateQueries: [{ queryKey: queryKeys.datasets.search.all() }],
    onError: (err) => {
      console.error("Failed to delete dataset:", err);
    },
  });
};
