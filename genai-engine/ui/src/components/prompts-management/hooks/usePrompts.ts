import type { PromptsFilters } from "../types";

import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMGetAllMetadataListResponse } from "@/lib/api-client/api-client";

export function usePrompts(taskId: string | undefined, filters: PromptsFilters) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAllAgenticPromptsApiV1TasksTaskIdPromptsGet">({
    method: "getAllAgenticPromptsApiV1TasksTaskIdPromptsGet",
    args: [
      {
        taskId: taskId!,
        page: filters.page ?? 0,
        page_size: filters.pageSize ?? 10,
        sort: filters.sort ?? "desc",
        created_after: filters.created_after ?? null,
        created_before: filters.created_before ?? null,
        model_provider: filters.model_provider ?? null,
        model_name: filters.model_name ?? null,
        llm_asset_names: filters.llm_asset_names ?? null,
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
    prompts: (data as LLMGetAllMetadataListResponse | undefined)?.llm_metadata ?? [],
    count: (data as LLMGetAllMetadataListResponse | undefined)?.count ?? 0,
    error,
    isLoading,
    refetch,
  };
}
