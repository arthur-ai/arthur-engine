import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMEval, MLEval } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

// Get an llm eval by name and version
export function useEval(taskId: string | undefined, evalName: string | undefined, evalVersion: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet">({
    method: "getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet",
    args: [encodePathParam(evalName!), evalVersion!, taskId!],
    enabled: !!taskId && !!evalName && !!evalVersion,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  return {
    eval: data as LLMEval | undefined,
    error,
    isLoading,
    refetch,
  };
}

// Get an ML eval by name and version
export function useMLEval(taskId: string | undefined, evalName: string | undefined, evalVersion?: string) {
  const { data, error, isLoading, refetch } = useApiQuery<"getMlEvalApiV2TasksTaskIdMlEvalsEvalNameVersionsEvalVersionGet">({
    method: "getMlEvalApiV2TasksTaskIdMlEvalsEvalNameVersionsEvalVersionGet",
    args: [encodePathParam(evalName!), evalVersion ?? "latest", taskId!],
    enabled: !!taskId && !!evalName,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  return {
    eval: data as MLEval | undefined,
    error,
    isLoading,
    refetch,
  };
}
