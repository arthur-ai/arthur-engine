import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { CreateAgenticPromptRequest, AgenticPrompt } from "@/lib/api-client/api-client";

export const useCreatePromptMutation = (taskId: string | undefined, onSuccess?: (promptData: AgenticPrompt) => void) => {
  const api = useApi();

  return useApiMutation<AgenticPrompt, { promptName: string; data: CreateAgenticPromptRequest }>({
    mutationFn: async ({ promptName, data }) => {
      if (!api || !taskId) throw new Error("API or task not available");

      const response = await api.api.saveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePost(promptName, taskId, data);

      return response.data;
    },
    invalidateQueries: [{ queryKey: ["getAllAgenticPromptsApiV1TasksTaskIdPromptsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to create prompt:", err);
    },
  });
};
