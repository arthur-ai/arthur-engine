import type { EvalVersionsFilters } from "../types";

import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMEvalsVersionListResponse } from "@/lib/api-client/api-client";

export function useEvalVersions(taskId: string | undefined, evalName: string | undefined, filters: EvalVersionsFilters = {}) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet">({
    method: "getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet",
    args: [
      {
        taskId: taskId!,
        evalName: evalName!,
        page: filters.page ?? 0,
        page_size: filters.pageSize ?? 10,
        sort: filters.sort ?? "desc",
        created_after: filters.created_after ?? null,
        created_before: filters.created_before ?? null,
        model_provider: filters.model_provider ?? null,
        model_name: filters.model_name ?? null,
        exclude_deleted: filters.exclude_deleted ?? false,
        min_version: filters.min_version ?? null,
        max_version: filters.max_version ?? null,
      },
    ],
    enabled: !!taskId && !!evalName,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  return {
    versions: (data as LLMEvalsVersionListResponse | undefined)?.versions ?? [],
    count: (data as LLMEvalsVersionListResponse | undefined)?.count ?? 0,
    error,
    isLoading,
    refetch,
  };
}
