import type { PendingChanges } from "./useDatasetLocalState";

import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";

export interface UseDatasetSaveMutationReturn {
  saveChanges: () => void;
  isSaving: boolean;
  canSave: boolean;
}

export function useDatasetSaveMutation(
  datasetId: string | undefined,
  pendingChanges: PendingChanges,
  hasUnsavedChanges: boolean,
  onSuccess: () => void
): UseDatasetSaveMutationReturn {
  const api = useApi();

  const { mutate: saveChanges, isPending: isSaving } = useApiMutation({
    mutationFn: async () => {
      if (!api || !datasetId)
        throw new Error("API or dataset ID not available");

      if (hasUnsavedChanges) {
        const request = {
          rows_to_add: pendingChanges.added.map((row) => ({
            data: row.data,
          })),
          rows_to_update: pendingChanges.updated.map((row) => ({
            id: row.id,
            data: row.data,
          })),
          rows_to_delete: pendingChanges.deleted,
        };

        return api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(
          datasetId,
          request
        );
      }

      return null;
    },
    invalidateQueries: [
      { queryKey: queryKeys.datasetVersions.list() },
      { queryKey: queryKeys.datasetVersions.all() },
      { queryKey: queryKeys.datasets.detail(datasetId!) },
      { queryKey: queryKeys.datasets.versions(datasetId!) },
    ],
    onSuccess,
    onError: (err) => {
      console.error("Failed to save changes:", err);
      alert("Failed to save changes. Please try again.");
    },
  });

  const canSave = hasUnsavedChanges && !isSaving;

  return {
    saveChanges: () => saveChanges(undefined),
    isSaving,
    canSave,
  };
}
