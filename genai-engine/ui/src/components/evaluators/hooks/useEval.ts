import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMEval } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

// Get an eval by name and version — works for both LLM and ML evals via v1 endpoint
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

// Alias for ML evals — same v1 endpoint, LLMEval is a superset (model fields are null for ML)
export function useMLEval(taskId: string | undefined, evalName: string | undefined, evalVersion?: string) {
  return useEval(taskId, evalName, evalVersion ?? "latest");
}
