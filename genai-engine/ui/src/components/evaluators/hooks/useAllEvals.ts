import { useApiQuery } from "@/hooks/useApiQuery";
import type { AllEvalsMetadataListResponse, EvalMetadataItem } from "@/lib/api-client/api-client";

export type { EvalMetadataItem };

interface UseAllEvalsFilters {
  page?: number;
  pageSize?: number;
  sort?: string;
  name?: string | null;
}

export function useAllEvals(taskId: string | undefined, filters: UseAllEvalsFilters = {}) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAllEvalsApiV2TasksTaskIdEvalsGet">({
    method: "getAllEvalsApiV2TasksTaskIdEvalsGet",
    args: [
      {
        taskId: taskId!,
        page: filters.page ?? 0,
        page_size: filters.pageSize ?? 50,
        sort: filters.sort ?? "desc",
        name: filters.name ?? null,
      },
    ],
    enabled: !!taskId,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  return {
    evals: (data as AllEvalsMetadataListResponse | undefined)?.evals ?? [],
    count: (data as AllEvalsMetadataListResponse | undefined)?.count ?? 0,
    error,
    isLoading,
    refetch,
  };
}
