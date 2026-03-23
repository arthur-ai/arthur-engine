import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";

export interface UpdateDatasetRowParams {
  datasetId: string;
  datasetVersion: number;
  rowId: string;
  columnName: string;
  newValue: string;
}

/**
 * Hook to update a dataset row with a new value from experiment output.
 * Creates a new dataset version with the updated row.
 */
export function useUpdateDatasetRowFromExperiment(datasetId: string) {
  const api = useApi();

  return useApiMutation<void, UpdateDatasetRowParams>({
    mutationFn: async ({ datasetId, datasetVersion, rowId, columnName, newValue }) => {
      if (!api) throw new Error("API client not available");

      const rowResponse = await api.api.getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet(datasetId, datasetVersion, rowId);

      const updatedData = rowResponse.data.data.map((col) =>
        col.column_name === columnName ? { column_name: col.column_name, column_value: newValue } : col
      );

      await api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(datasetId, {
        rows_to_add: [],
        rows_to_delete: [],
        rows_to_update: [{ id: rowId, data: updatedData }],
      });
    },
    invalidateQueries: [
      { queryKey: queryKeys.datasetVersions.list() },
      { queryKey: queryKeys.datasetVersions.all() },
      { queryKey: queryKeys.datasets.detail(datasetId) },
      { queryKey: queryKeys.datasets.versions(datasetId) },
    ],
  });
}
