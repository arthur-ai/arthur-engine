import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { CreateEvalRequest, Eval } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

export const useCreateEvalMutation = (taskId: string | undefined, onSuccess?: (evalData: Eval) => void) => {
  const api = useApi();

  return useApiMutation<Eval, { evalName: string; data: CreateEvalRequest }>({
    mutationFn: async ({ evalName, data }) => {
      if (!api || !taskId) throw new Error("API or task not available");

      const response = await api.api.saveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePost(encodePathParam(evalName), taskId, data);

      return response.data;
    },
    invalidateQueries: [{ queryKey: ["getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to create eval:", err);
    },
  });
};
