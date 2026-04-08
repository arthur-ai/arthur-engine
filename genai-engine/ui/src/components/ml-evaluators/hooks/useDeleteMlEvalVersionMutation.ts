import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { MLEval } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

export const useDeleteMlEvalVersionMutation = (taskId: string | undefined, evalName: string | undefined, onSuccess?: () => void) => {
  const api = useApi();

  return useApiMutation<MLEval, { version: string }>({
    mutationFn: async ({ version }) => {
      if (!api || !taskId || !evalName) throw new Error("API or task not available");

      const response = await api.api.deleteMlEvalVersionApiV2TasksTaskIdMlEvalsEvalNameVersionsEvalVersionDelete(
        encodePathParam(evalName),
        version,
        taskId
      );

      return response.data;
    },
    invalidateQueries: [
      { queryKey: ["getAllMlEvalsApiV2TasksTaskIdMlEvalsGet"] },
      { queryKey: ["listMlEvalVersionsApiV2TasksTaskIdMlEvalsEvalNameVersionsGet"] },
    ],
    onSuccess,
    onError: (err) => {
      console.error("Failed to delete ML eval version:", err);
    },
  });
};
