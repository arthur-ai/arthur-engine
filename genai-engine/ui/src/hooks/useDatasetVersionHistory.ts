import { useApiQuery } from "./useApiQuery";

export function useDatasetVersionHistory(
  datasetId: string | undefined,
  page: number = 0,
  pageSize: number = 50
) {
  const { data, error, isLoading, refetch } =
    useApiQuery<"getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet">({
      method: "getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet",
      args: [
        {
          datasetId: datasetId!,
          page,
          page_size: pageSize,
          sort: "desc", // Most recent first
        },
      ] as const,
      enabled: !!datasetId,
      queryOptions: {
        staleTime: 2000,
        refetchOnWindowFocus: true,
      },
    });

  return {
    versions: data?.versions || [],
    totalCount: data?.total_count || 0,
    isLoading,
    error,
    refetch,
  };
}
