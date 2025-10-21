import { useApiQuery } from "./useApiQuery";

import { GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetParams } from "@/lib/api-client/api-client";

export function useDatasetVersionData(
  datasetId: string | undefined,
  versionNumber: number | undefined,
  page: number = 0,
  pageSize: number = 25
) {
  const params: GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetParams =
    {
      datasetId: datasetId!,
      versionNumber: versionNumber!,
      page,
      page_size: pageSize,
      sort: "asc",
    };

  const { data, error, isLoading, refetch } =
    useApiQuery<"getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet">(
      {
        method:
          "getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet",
        args: [params] as const,
        enabled: !!datasetId && versionNumber !== undefined,
        queryOptions: {
          staleTime: 2000,
          refetchOnWindowFocus: true,
        },
      }
    );

  return {
    version: data,
    error,
    isLoading,
    refetch,
  };
}
