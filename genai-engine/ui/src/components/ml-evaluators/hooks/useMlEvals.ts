import { useApiQuery } from "@/hooks/useApiQuery";
import type { MLGetAllMetadataListResponse } from "@/lib/api-client/api-client";

export function useMlEvals(taskId: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAllMlEvalsApiV2TasksTaskIdMlEvalsGet">({
    method: "getAllMlEvalsApiV2TasksTaskIdMlEvalsGet",
    args: [taskId!],
    enabled: !!taskId,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  return {
    evals: (data as MLGetAllMetadataListResponse | undefined)?.ml_metadata ?? [],
    count: (data as MLGetAllMetadataListResponse | undefined)?.count ?? 0,
    error,
    isLoading,
    refetch,
  };
}
