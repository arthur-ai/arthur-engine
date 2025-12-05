import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

const DEFAULT_PAGE_SIZE = 100;
const DEFAULT_SORT = "desc";

export const useBackendPromptVersions = (promptName: string) => {
  const api = useApi()!;
  const { task } = useTask();

  return useQuery({
    queryKey: queryKeys.prompts.versions(task!.id!, promptName),
    queryFn: async () => {
      const response = await api.api.getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet({
        taskId: task!.id!,
        promptName,
        page_size: DEFAULT_PAGE_SIZE,
        sort: DEFAULT_SORT,
      });
      return response.data;
    },
    enabled: !!promptName,
  });
};
