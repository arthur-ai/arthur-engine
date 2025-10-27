import { useApiQuery } from "./useApiQuery";

import type { DatasetResponse } from "@/lib/api-client/api-client";

export function useDataset(datasetId: string | undefined) {
  const { data, error, isLoading, refetch } =
    useApiQuery<"getDatasetApiV2DatasetsDatasetIdGet">({
      method: "getDatasetApiV2DatasetsDatasetIdGet",
      args: [datasetId!] as const,
      enabled: !!datasetId,
      queryOptions: {
        staleTime: 2000,
        refetchOnWindowFocus: true,
      },
    });

  return {
    dataset: data as DatasetResponse | undefined,
    error,
    isLoading,
    refetch,
  };
}
