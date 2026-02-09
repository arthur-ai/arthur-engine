import type { DatasetAction, DatasetUpdateParams, PendingChanges, UseDatasetMutationsReturn } from "./types";

import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";
import type { ColumnDefaults } from "@/types/dataset";
import { fetchAllDatasetRows } from "@/utils/datasetApi";

interface UseDatasetMutationsParams {
  datasetId: string;
  currentVersion: number | undefined;
  pendingChanges: PendingChanges;
  hasUnsavedChanges: boolean;
  dispatch: React.Dispatch<DatasetAction>;
  showSnackbar: (message: string, severity: "success" | "error") => void;
}

export function useDatasetMutations({
  datasetId,
  currentVersion,
  pendingChanges,
  hasUnsavedChanges,
  dispatch,
  showSnackbar,
}: UseDatasetMutationsParams): UseDatasetMutationsReturn {
  const api = useApi();

  const invalidateQueries = [
    { queryKey: queryKeys.datasetVersions.list() },
    { queryKey: queryKeys.datasetVersions.all() },
    { queryKey: queryKeys.datasets.detail(datasetId) },
    { queryKey: queryKeys.datasets.versions(datasetId) },
  ];

  const save = useApiMutation<void, void>({
    mutationFn: async () => {
      if (!api || !datasetId) {
        throw new Error("API or dataset ID not available");
      }

      if (!hasUnsavedChanges) {
        return;
      }

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

      await api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(datasetId, request);
    },
    invalidateQueries,
    onSuccess: () => {
      dispatch({ type: "DATA/CLEAR_CHANGES" });
      dispatch({ type: "VERSION/RESET_TO_LATEST" });
      showSnackbar("Changes saved successfully!", "success");
    },
    onError: (error) => {
      showSnackbar(error.message || "Failed to save changes", "error");
    },
  });

  const fillColumn = useApiMutation<void, { columnName: string; value: string }>({
    mutationFn: async ({ columnName, value }) => {
      if (!api || !datasetId || currentVersion === undefined) {
        throw new Error("API, dataset ID, or version number not available");
      }

      const allRows = await fetchAllDatasetRows(api, datasetId, currentVersion);

      const updatedRows = allRows.map((row) => ({
        id: row.id,
        data: row.data.map((col) => (col.column_name === columnName ? { ...col, column_value: value } : col)),
      }));

      await api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(datasetId, {
        rows_to_add: [],
        rows_to_delete: [],
        rows_to_update: updatedRows,
      });
    },
    invalidateQueries,
    onSuccess: () => {
      dispatch({ type: "UI/CLOSE_FILL_MODAL" });
      dispatch({ type: "VERSION/RESET_TO_LATEST" });
      showSnackbar("Column filled successfully!", "success");
    },
    onError: (error) => {
      showSnackbar(error.message || "Failed to fill column", "error");
    },
  });

  const applyDefaults = useApiMutation<void, { columnDefaults: ColumnDefaults }>({
    mutationFn: async ({ columnDefaults }) => {
      if (!api || !datasetId || currentVersion === undefined) {
        throw new Error("API, dataset ID, or version number not available");
      }

      const columnsToApply = Object.entries(columnDefaults).filter(([, config]) => config.type !== "none");

      if (columnsToApply.length === 0) {
        throw new Error("No defaults configured to apply");
      }

      const allRows = await fetchAllDatasetRows(api, datasetId, currentVersion);

      const updatedRows = allRows.map((row) => {
        const existingColumnNames = new Set(row.data.map((col) => col.column_name));

        const existingData = row.data.map((col) => {
          const config = columnDefaults[col.column_name];

          if (!config || config.type === "none") {
            return col;
          }

          if (config.type === "timestamp") {
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
        });

        const newColumns = columnsToApply
          .filter(([columnName]) => !existingColumnNames.has(columnName))
          .map(([columnName, config]) => ({
            column_name: columnName,
            column_value: config.type === "timestamp" ? new Date(row.created_at).toISOString() : config.type === "static" ? (config.value ?? "") : "",
          }));

        return {
          id: row.id,
          data: [...existingData, ...newColumns],
        };
      });

      await api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(datasetId, {
        rows_to_add: [],
        rows_to_delete: [],
        rows_to_update: updatedRows,
      });
    },
    invalidateQueries,
    onSuccess: () => {
      dispatch({ type: "VERSION/RESET_TO_LATEST" });
      showSnackbar("Defaults applied successfully!", "success");
    },
    onError: (error) => {
      showSnackbar(error.message || "Failed to apply defaults", "error");
    },
  });

  const updateDataset = useApiMutation<void, DatasetUpdateParams>({
    mutationFn: async (params) => {
      if (!api || !datasetId) {
        throw new Error("API or dataset ID not available");
      }

      await api.api.updateDatasetApiV2DatasetsDatasetIdPatch(datasetId, {
        name: params.name,
        description: params.description ?? null,
        metadata: params.metadata ?? null,
      });
    },
    invalidateQueries: [{ queryKey: queryKeys.datasets.search.all() }, { queryKey: queryKeys.datasets.detail(datasetId) }],
    onError: (error) => {
      showSnackbar(error.message || "Failed to update dataset", "error");
    },
  });

  return {
    save,
    fillColumn,
    applyDefaults,
    updateDataset,
  };
}
