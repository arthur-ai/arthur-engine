import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";
import { createDataset } from "@/services/datasetService";
import { Dataset, DatasetFormData } from "@/types/dataset";

export const useCreateDatasetMutation = (
  taskId: string | undefined,
  onSuccess: (dataset: Dataset) => void
) => {
  const api = useApi();

  return useApiMutation<Dataset, DatasetFormData>({
    mutationFn: async (formData: DatasetFormData) => {
      if (!api || !taskId) throw new Error("API or task not available");
      return createDataset(api, taskId, formData);
    },
    invalidateQueries: [{ queryKey: queryKeys.datasets.search.all() }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to create dataset:", err);
    },
  });
};
