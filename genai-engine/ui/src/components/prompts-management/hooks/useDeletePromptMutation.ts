import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";

export const useDeletePromptMutation = (taskId: string | undefined, onSuccess?: () => void) => {
  const api = useApi();

  return useApiMutation<void, string>({
    mutationFn: async (promptName: string) => {
      if (!api || !taskId) throw new Error("API or task not available");

      await api.api.deleteAgenticPromptApiV1TasksTaskIdPromptsPromptNameDelete(promptName, taskId);
    },
    invalidateQueries: [{ queryKey: ["getAllAgenticPromptsApiV1TasksTaskIdPromptsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to delete prompt:", err);
    },
  });
};
