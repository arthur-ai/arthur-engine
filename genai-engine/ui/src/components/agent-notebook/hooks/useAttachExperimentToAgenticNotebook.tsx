import { useMutation } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";

export const useAttachExperimentToAgenticNotebook = (notebookId: string) => {
  const { api } = useApi()!;

  return useMutation({
    mutationFn: async (experimentId: string) => {
      const response = await api.attachNotebookToAgenticExperimentApiV1AgenticExperimentsExperimentIdNotebookPatch({
        experimentId,
        notebook_id: notebookId,
      });

      return response.data;
    },
  });
};
