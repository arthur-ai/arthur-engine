import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { encodePathParam } from "@/utils/url";

export const useDeleteMlEvalVersionMutation = (taskId: string | undefined, evalName: string | undefined, onSuccess?: () => void) => {
  const api = useApi();

  return useApiMutation<void, { version: string }>({
    mutationFn: async ({ version }) => {
      if (!api || !taskId || !evalName) throw new Error("API or task not available");

      await api.api.softDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDelete(encodePathParam(evalName), version, taskId);
    },
    invalidateQueries: [
      { queryKey: ["getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet"] },
      { queryKey: ["getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet"] },
    ],
    onSuccess,
    onError: (err) => {
      console.error("Failed to delete ML eval version:", err);
    },
  });
};
