import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { encodePathParam } from "@/utils/url";

export const useDeletePromptVersionMutation = (taskId: string | undefined, promptName: string, onSuccess?: () => void) => {
  const api = useApi();

  return useApiMutation<void, number>({
    mutationFn: async (version: number) => {
      if (!api || !taskId) throw new Error("API or task not available");

      await api.api.deleteAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionDelete(
        encodePathParam(promptName),
        version.toString(),
        taskId
      );
    },
    invalidateQueries: [{ queryKey: ["getAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to delete prompt version:", err);
    },
  });
};
