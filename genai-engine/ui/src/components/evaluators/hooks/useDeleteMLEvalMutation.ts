import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { encodePathParam } from "@/utils/url";

export const useDeleteMLEvalMutation = (taskId: string | undefined, onSuccess?: () => void) => {
  const api = useApi();

  return useApiMutation<void, string>({
    mutationFn: async (evalName: string) => {
      if (!api || !taskId) throw new Error("API or task not available");

      await api.api.deleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDelete(encodePathParam(evalName), taskId);
    },
    invalidateQueries: [{ queryKey: ["getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to delete ML eval:", err);
    },
  });
};
