import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { AgenticPrompt } from "@/lib/api-client/api-client";

interface AddTagVariables {
  promptName: string;
  promptVersion: string;
  taskId: string;
  data: { tag: string };
}

export function useAddTagToPromptVersionMutation() {
  const api = useApi();

  return useApiMutation<AgenticPrompt, AddTagVariables>({
    mutationFn: async ({ promptName, promptVersion, taskId, data }: AddTagVariables) => {
      if (!api) throw new Error("API not available");

      const response = await api.api.addTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut(
        promptName,
        promptVersion,
        taskId,
        data
      );
      return response.data;
    },
    invalidateQueries: [
      { queryKey: ["getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet"] },
      { queryKey: ["getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet"] },
    ],
  });
}
