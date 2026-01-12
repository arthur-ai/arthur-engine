import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

export const useAttachExperimentToAgenticNotebook = (notebookId: string) => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;

  return useMutation({
    mutationFn: async (experimentId: string) => {
      const response = await api.attachNotebookToAgenticExperimentApiV1AgenticExperimentsExperimentIdNotebookPatch({
        experimentId,
        notebook_id: notebookId,
      });

      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agentNotebooks.byId(notebookId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.agentNotebooks.history(notebookId) });
    },
  });
};
