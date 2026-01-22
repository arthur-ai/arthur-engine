import type { UseDatasetQueriesReturn } from "./types";

import { useApiQuery } from "@/hooks/useApiQuery";
import type { DatasetResponse, DatasetVersionResponse, ListDatasetVersionsResponse } from "@/lib/api-client/api-client";

interface UseDatasetQueriesParams {
  datasetId: string;
  selectedVersion: number | undefined;
  page: number;
  rowsPerPage: number;
}

export function useDatasetQueries({ datasetId, selectedVersion, page, rowsPerPage }: UseDatasetQueriesParams): UseDatasetQueriesReturn {
  const {
    data: datasetData,
    isLoading: datasetLoading,
    error: datasetError,
    refetch: refetchDataset,
  } = useApiQuery<"getDatasetApiV2DatasetsDatasetIdGet">({
    method: "getDatasetApiV2DatasetsDatasetIdGet",
    args: [datasetId] as const,
    enabled: !!datasetId,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
    },
  });

  const dataset = datasetData as DatasetResponse | undefined;

  const { data: latestVersionData, isLoading: latestVersionLoading } = useApiQuery<"getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet">({
    method: "getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet",
    args: [
      {
        datasetId: datasetId,
        latest_version_only: true,
        page: 0,
        page_size: 1,
      },
    ] as const,
    enabled: !!datasetId,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
    },
  });

  const latestVersion = (latestVersionData as ListDatasetVersionsResponse | undefined)?.versions?.[0]?.version_number;

  const currentVersion = selectedVersion ?? latestVersion;

  const {
    data: versionDataResponse,
    isLoading: versionLoading,
    error: versionError,
  } = useApiQuery<"getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet">({
    method: "getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet",
    args: [
      {
        datasetId: datasetId,
        versionNumber: currentVersion!,
        page,
        page_size: rowsPerPage,
        sort: "asc",
      },
    ] as const,
    enabled: !!datasetId && currentVersion !== undefined,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
    },
  });

  const versionData = versionDataResponse as DatasetVersionResponse | undefined;

  return {
    dataset,
    datasetLoading,
    datasetError: datasetError as Error | null,
    refetchDataset,

    latestVersion,
    latestVersionLoading,

    versionData,
    versionLoading,
    versionError: versionError as Error | null,

    currentVersion,
    isLoading: datasetLoading || latestVersionLoading || versionLoading,
    totalRowCount: versionData?.total_count ?? 0,
  };
}
