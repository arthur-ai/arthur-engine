import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { DatasetResponse, NewDatasetRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { createDataset } from "@/services/datasetService";

export const useCreateDatasetMutation = (taskId: string | undefined, onSuccess: (dataset: DatasetResponse) => void) => {
  const api = useApi();

  return useApiMutation<DatasetResponse, NewDatasetRequest>({
    mutationFn: async (formData: NewDatasetRequest) => {
      if (!api || !taskId) throw new Error("API or task not available");
      return createDataset(api, taskId, formData);
    },
    invalidateQueries: [{ queryKey: queryKeys.datasets.search.all() }],
    onSuccess: (dataset) => {
      track(EVENT_NAMES.DATASET_CREATED, { dataset_id: dataset.id, task_id: taskId });
      onSuccess(dataset);
    },
    onError: (err) => {
      console.error("Failed to create dataset:", err);
    },
  });
};
