import { useApiQuery } from "@/hooks/useApiQuery";
import type { MLEval } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

export function useMlEval(taskId: string | undefined, evalName: string | undefined, evalVersion: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getMlEvalApiV2TasksTaskIdMlEvalsEvalNameVersionsEvalVersionGet">({
    method: "getMlEvalApiV2TasksTaskIdMlEvalsEvalNameVersionsEvalVersionGet",
    args: [encodePathParam(evalName!), evalVersion!, taskId!],
    enabled: !!taskId && !!evalName && !!evalVersion,
    queryOptions: {
      staleTime: 2000,
    },
  });

  return {
    eval: data as MLEval | undefined,
    error,
    isLoading,
    refetch,
  };
}
