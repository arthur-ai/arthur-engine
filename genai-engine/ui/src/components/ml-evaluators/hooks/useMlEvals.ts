import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMGetAllMetadataListResponse, LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";

// Fetches all evals via v1 endpoint and filters to ML types only
export function useMlEvals(taskId: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet">({
    method: "getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet",
    args: [
      {
        taskId: taskId!,
        page: 0,
        page_size: 500,
        sort: "desc",
        created_after: null,
        created_before: null,
        model_provider: null,
        model_name: null,
        llm_asset_names: null,
      },
    ],
    enabled: !!taskId,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  const allEvals = (data as LLMGetAllMetadataListResponse | undefined)?.llm_metadata ?? [];
  const mlEvals = allEvals.filter((e: LLMGetAllMetadataResponse) => e.eval_type !== "llm_as_a_judge");

  return {
    evals: mlEvals,
    count: mlEvals.length,
    error,
    isLoading,
    refetch,
  };
}
