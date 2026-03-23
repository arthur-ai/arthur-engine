import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";

export const useDeleteEvalMutation = (taskId: string | undefined, onSuccess?: () => void) => {
  const api = useApi();

  return useApiMutation<void, string>({
    mutationFn: async (evalName: string) => {
      if (!api || !taskId) throw new Error("API or task not available");

      await api.api.deleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDelete(evalName, taskId);
    },
    invalidateQueries: [{ queryKey: ["getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to delete eval:", err);
    },
  });
};
