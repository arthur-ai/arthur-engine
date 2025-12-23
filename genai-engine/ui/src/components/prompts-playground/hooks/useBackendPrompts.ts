import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const useBackendPrompts = () => {
  const api = useApi()!;
  const { task } = useTask()!;

  return useQuery({
    queryKey: queryKeys.prompts.all(task!.id!),
    queryFn: async () => {
      const response = await api.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({ taskId: task!.id! });
      return response.data;
    },
  });
};
