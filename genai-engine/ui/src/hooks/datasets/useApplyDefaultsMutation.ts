import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";
import type { ColumnDefaults } from "@/types/dataset";
import { fetchAllDatasetRows } from "@/utils/datasetApi";

interface ApplyDefaultsParams {
  columnDefaults: ColumnDefaults;
}

export interface UseApplyDefaultsMutationReturn {
  applyDefaults: (params: ApplyDefaultsParams) => void;
  isApplying: boolean;
}

/**
 * Hook to apply column defaults to all existing rows in a dataset.
 * For timestamp defaults, uses each row's created_at timestamp.
 * For static defaults, uses the configured value.
 */
export function useApplyDefaultsMutation(
  datasetId: string | undefined,
  versionNumber: number | undefined,
  onSuccess: () => void,
  onError?: (error: Error) => void
): UseApplyDefaultsMutationReturn {
  const api = useApi();

  const { mutate: applyDefaults, isPending: isApplying } = useApiMutation({
    mutationFn: async ({ columnDefaults }: ApplyDefaultsParams) => {
      if (!api || !datasetId || versionNumber === undefined) {
        throw new Error("API, dataset ID, or version number not available");
      }

      // Get columns that have non-none defaults
      const columnsToApply = Object.entries(columnDefaults).filter(
        ([, config]) => config.type !== "none"
      );

      if (columnsToApply.length === 0) {
        throw new Error("No defaults configured to apply");
      }

      const allRows = await fetchAllDatasetRows(api, datasetId, versionNumber);

      const updatedRows = allRows.map((row) => ({
        id: row.id,
        data: row.data.map((col) => {
          const config = columnDefaults[col.column_name];

          if (!config || config.type === "none") {
            return col;
          }

          if (config.type === "timestamp") {
            // Use the row's created_at timestamp
            return {
              ...col,
              column_value: new Date(row.created_at).toISOString(),
            };
          }

          if (config.type === "static") {
            return {
              ...col,
              column_value: config.value ?? "",
            };
          }

          return col;
        }),
      }));

      return api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(
        datasetId,
        {
          rows_to_add: [],
          rows_to_delete: [],
          rows_to_update: updatedRows,
        }
      );
    },
    invalidateQueries: [
      { queryKey: queryKeys.datasetVersions.list() },
      { queryKey: queryKeys.datasetVersions.all() },
      { queryKey: queryKeys.datasets.detail(datasetId!) },
      { queryKey: queryKeys.datasets.versions(datasetId!) },
    ],
    onSuccess,
    onError: (err) => {
      console.error("Failed to apply defaults:", err);
      if (onError) {
        onError(err as Error);
      }
    },
  });

  return {
    applyDefaults: (params: ApplyDefaultsParams) => applyDefaults(params),
    isApplying,
  };
}
