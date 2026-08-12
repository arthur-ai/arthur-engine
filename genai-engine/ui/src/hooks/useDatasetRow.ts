import { useApiQuery } from "./useApiQuery";

/**
 * Fetches a single dataset version row. Shared by the dataset row drawer,
 * the experiment test-case detail modal, and the update-row modal so they
 * hit the same react-query cache entry ([method, datasetId, version, rowId]).
 */
export function useDatasetRow(datasetId: string | undefined, versionNumber: number | undefined, rowId: string | null | undefined, enabled = true) {
  return useApiQuery<"getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet">({
    method: "getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet",
    args: [datasetId ?? "", versionNumber ?? 0, rowId ?? ""],
    enabled: enabled && !!datasetId && versionNumber !== undefined && !!rowId,
  });
}
