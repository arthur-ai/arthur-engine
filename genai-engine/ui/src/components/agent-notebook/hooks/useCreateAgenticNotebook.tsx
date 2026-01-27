import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticNotebookDetail, CreateAgenticNotebookRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  onSuccess?: (data: AgenticNotebookDetail) => void;
};

export const useCreateAgenticNotebook = (opts: Opts = {}) => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;
  const { task } = useTask();

  return useMutation({
    mutationFn: async (data: CreateAgenticNotebookRequest) => {
      const response = await api.createAgenticNotebookApiV1TasksTaskIdAgenticNotebooksPost(task!.id, data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agentNotebooks.all(task!.id) });
      opts.onSuccess?.(data);
    },
  });
};
