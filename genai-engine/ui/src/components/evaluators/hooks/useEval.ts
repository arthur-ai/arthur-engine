import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMEval } from "@/lib/api-client/api-client";

// Get an llm eval by name and version
export function useEval(taskId: string | undefined, evalName: string | undefined, evalVersion: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet">({
    method: "getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet",
    args: [evalName!, evalVersion!, taskId!],
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
