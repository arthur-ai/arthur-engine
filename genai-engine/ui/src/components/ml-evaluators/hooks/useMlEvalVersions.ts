import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMEvalsVersionListResponse } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

export function useMlEvalVersions(taskId: string | undefined, evalName: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet">({
    method: "getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet",
    args: [
      {
        taskId: taskId!,
        evalName: encodePathParam(evalName ?? ""),
        page: 0,
        page_size: 100,
        sort: "desc",
        created_after: null,
        created_before: null,
        model_provider: null,
        model_name: null,
        exclude_deleted: false,
        min_version: null,
        max_version: null,
      },
    ],
    enabled: !!taskId && !!evalName,
    queryOptions: {
      staleTime: 2000,
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
