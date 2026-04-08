import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { CreateMLEvalRequest, MLEval } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

export const useCreateMlEvalMutation = (taskId: string | undefined, onSuccess?: (evalData: MLEval) => void) => {
  const api = useApi();

  return useApiMutation<MLEval, { evalName: string; data: CreateMLEvalRequest }>({
    mutationFn: async ({ evalName, data }) => {
      if (!api || !taskId) throw new Error("API or task not available");

      const response = await api.api.saveMlEvalApiV2TasksTaskIdMlEvalsEvalNamePost(encodePathParam(evalName), taskId, data);

      return response.data;
    },
    invalidateQueries: [{ queryKey: ["getAllMlEvalsApiV2TasksTaskIdMlEvalsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to create ML eval:", err);
    },
  });
};
