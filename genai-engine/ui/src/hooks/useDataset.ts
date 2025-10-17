import { useApiQuery } from "./useApiQuery";

import { Dataset } from "@/types/dataset";

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
    dataset: data as Dataset | undefined,
    error,
    isLoading,
    refetch,
  };
}
