import { useApiQuery } from "./useApiQuery";

import { ListDatasetVersionsResponse } from "@/lib/api-client/api-client";

export function useDatasetLatestVersion(datasetId: string | undefined) {
  const { data, error, isLoading, refetch } =
    useApiQuery<"getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet">({
      method: "getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet",
      args: [
        {
          datasetId: datasetId!,
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

  const latestVersion =
    data && (data as ListDatasetVersionsResponse).versions?.[0];

  return {
    latestVersion,
    hasVersions: !!latestVersion,
    error,
    isLoading,
    refetch,
  };
}
