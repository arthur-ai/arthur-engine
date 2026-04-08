import { useApiQuery } from "@/hooks/useApiQuery";
import type { MLEvalsVersionListResponse } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

export function useMlEvalVersions(taskId: string | undefined, evalName: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"listMlEvalVersionsApiV2TasksTaskIdMlEvalsEvalNameVersionsGet">({
    method: "listMlEvalVersionsApiV2TasksTaskIdMlEvalsEvalNameVersionsGet",
    args: [encodePathParam(evalName ?? ""), taskId!],
    enabled: !!taskId && !!evalName,
    queryOptions: {
      staleTime: 2000,
    },
  });

  return {
    versions: (data as MLEvalsVersionListResponse | undefined)?.versions ?? [],
    count: (data as MLEvalsVersionListResponse | undefined)?.count ?? 0,
    error,
    isLoading,
    refetch,
  };
}
