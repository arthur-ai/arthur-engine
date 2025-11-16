import type { PromptVersionsFilters } from "../types";

import { useApiQuery } from "@/hooks/useApiQuery";
import type { AgenticPromptVersionListResponse } from "@/lib/api-client/api-client";

export function usePromptVersions(taskId: string | undefined, promptName: string | undefined, filters: PromptVersionsFilters = {}) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet">({
    method: "getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet",
    args: [
      {
        taskId: taskId!,
        promptName: promptName!,
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
    enabled: !!taskId && !!promptName,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  return {
    versions: (data as AgenticPromptVersionListResponse | undefined)?.versions ?? [],
    count: (data as AgenticPromptVersionListResponse | undefined)?.count ?? 0,
    error,
    isLoading,
    refetch,
  };
}
