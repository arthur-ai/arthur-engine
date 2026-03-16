import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticNotebookDetail, UpdateAgenticNotebookRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  onSuccess?: (data: AgenticNotebookDetail) => void;
};

export const useUpdateAgenticNotebook = (opts: Opts = {}) => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;
  const { task } = useTask();

  return useMutation({
    mutationFn: async ({ notebookId, request }: { notebookId: string; request: UpdateAgenticNotebookRequest }) => {
      const response = await api.updateAgenticNotebookApiV1AgenticNotebooksNotebookIdPut(notebookId, request);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agentNotebooks.all(task!.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.agentNotebooks.byId(data.id) });
      opts.onSuccess?.(data);
    },
  });
};
