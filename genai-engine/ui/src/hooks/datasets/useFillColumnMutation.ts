import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";
import { fetchAllDatasetRows } from "@/utils/datasetApi";

interface FillColumnParams {
  columnName: string;
  value: string;
}

export interface UseFillColumnMutationReturn {
  fillColumn: (params: FillColumnParams) => void;
  isFilling: boolean;
}

export function useFillColumnMutation(
  datasetId: string | undefined,
  versionNumber: number | undefined,
  onSuccess: () => void,
  onError?: (error: Error) => void
): UseFillColumnMutationReturn {
  const api = useApi();

  const { mutate: fillColumn, isPending: isFilling } = useApiMutation({
    mutationFn: async ({ columnName, value }: FillColumnParams) => {
      if (!api || !datasetId || versionNumber === undefined) {
        throw new Error("API, dataset ID, or version number not available");
      }

      const allRows = await fetchAllDatasetRows(api, datasetId, versionNumber);

      const updatedRows = allRows.map((row) => ({
        id: row.id,
        data: row.data.map((col) => (col.column_name === columnName ? { ...col, column_value: value } : col)),
      }));

      return api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(datasetId, {
        rows_to_add: [],
        rows_to_delete: [],
        rows_to_update: updatedRows,
      });
    },
    invalidateQueries: [
      { queryKey: queryKeys.datasetVersions.list() },
      { queryKey: queryKeys.datasetVersions.all() },
      { queryKey: queryKeys.datasets.detail(datasetId!) },
      { queryKey: queryKeys.datasets.versions(datasetId!) },
    ],
    onSuccess,
    onError: (err) => {
      console.error("Failed to fill column:", err);
      if (onError) {
        onError(err as Error);
      }
    },
  });

  return {
    fillColumn: (params: FillColumnParams) => fillColumn(params),
    isFilling,
  };
}
