import { useMemo } from "react";

import { useApiQuery } from "./useApiQuery";

import type { DatasetResponse } from "@/lib/api-client/api-client";
import { buildFetchDatasetsParams } from "@/services/datasetService";
import type { DatasetFilters } from "@/types/dataset";

export function useDatasets(
  taskId: string | undefined,
  filters: DatasetFilters
) {
  const params = buildFetchDatasetsParams(filters);

  const { data, error, isLoading, refetch } =
    useApiQuery<"getDatasetsApiV2DatasetsSearchGet">({
      method: "getDatasetsApiV2DatasetsSearchGet",
      args: [params] as const,
      enabled: !!taskId,
      queryOptions: {
        staleTime: 2000,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
      },
    });

  const taskDatasets = useMemo(
    () =>
      data?.datasets?.filter(
        (dataset) => dataset.metadata?.task_id === taskId
      ) ?? [],
    [data, taskId]
  );

  return {
    datasets: taskDatasets as DatasetResponse[],
    count: taskDatasets.length,
    error,
    isLoading,
    refetch,
  };
}
