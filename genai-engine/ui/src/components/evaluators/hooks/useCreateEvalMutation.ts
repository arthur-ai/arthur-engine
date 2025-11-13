import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { CreateEvalRequest, LLMEval } from "@/lib/api-client/api-client";

export const useCreateEvalMutation = (
  taskId: string | undefined,
  onSuccess?: (eval: LLMEval) => void
) => {
  const api = useApi();

  return useApiMutation<LLMEval, { evalName: string; data: CreateEvalRequest }>({
    mutationFn: async ({ evalName, data }) => {
      if (!api || !taskId) throw new Error("API or task not available");
      
      const response = await api.api.saveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePost(
        evalName,
        taskId,
        data
      );
      
      return response.data;
    },
    invalidateQueries: [
      { queryKey: ["getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet"] },
    ],
    onSuccess,
    onError: (err) => {
      console.error("Failed to create eval:", err);
    },
  });
};

