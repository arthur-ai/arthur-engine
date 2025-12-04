import { useApiQuery } from "./useApiQuery";

import type { DatasetResponse } from "@/lib/api-client/api-client";
import { buildFetchDatasetsParams } from "@/services/datasetService";
import type { DatasetFilters } from "@/types/dataset";

export function useDatasets(
  taskId: string | undefined,
  filters: DatasetFilters,
  options?: { enabled?: boolean }
) {
  const params = buildFetchDatasetsParams(taskId, filters);

  const { data, error, isLoading, refetch } =
    useApiQuery<"getDatasetsApiV2TasksTaskIdDatasetsSearchGet">({
      method: "getDatasetsApiV2TasksTaskIdDatasetsSearchGet",
      args: [params] as const,
      enabled: !!taskId && (options?.enabled ?? true),
      queryOptions: {
        staleTime: 2000,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
      },
    });

  return {
    datasets: (data?.datasets ?? []) as DatasetResponse[],
    count: data?.datasets?.length ?? 0,
    error,
    isLoading,
    refetch,
  };
}
