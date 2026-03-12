import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { encodePathParam } from "@/utils/url";

interface DeleteTagVariables {
  promptName: string;
  promptVersion: string;
  tag: string;
  taskId: string;
}

export function useDeleteTagFromPromptVersionMutation() {
  const api = useApi();

  return useApiMutation<void, DeleteTagVariables>({
    mutationFn: async ({ promptName, promptVersion, tag, taskId }: DeleteTagVariables) => {
      if (!api) throw new Error("API not available");

      await api.api.deleteTagFromAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsTagDelete(
        encodePathParam(promptName),
        promptVersion,
        encodePathParam(tag),
        taskId
      );
    },
    invalidateQueries: [
      { queryKey: ["getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet"] },
      { queryKey: ["getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet"] },
    ],
  });
}
