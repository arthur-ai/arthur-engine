import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const useBackendPromptVersion = (promptName: string, version: string) => {
  const api = useApi()!;
  const { task } = useTask();

  return useQuery({
    queryKey: queryKeys.prompts.version(task!.id!, promptName, version),
    queryFn: async () => {
      const response = await api.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(promptName, version, task!.id);
      return response.data;
    },
    enabled: !!promptName && !!version && !!task?.id,
  });
};
