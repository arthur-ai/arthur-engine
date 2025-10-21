import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type {
  DatasetResponse,
  NewDatasetRequest,
} from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { createDataset } from "@/services/datasetService";

export const useCreateDatasetMutation = (
  taskId: string | undefined,
  onSuccess: (dataset: DatasetResponse) => void
) => {
  const api = useApi();

  return useApiMutation<DatasetResponse, NewDatasetRequest>({
    mutationFn: async (formData: NewDatasetRequest) => {
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
