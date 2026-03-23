import { useMutation } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { AgenticNotebookDetail, SetAgenticNotebookStateRequest } from "@/lib/api-client/api-client";

type Opts = {
  onSuccess?: (data: AgenticNotebookDetail) => Promise<void>;
  onError?: (error: Error) => void;
};

export const useSaveAgenticNotebookState = (notebookId: string, { onSuccess, onError }: Opts = {}) => {
  const { api } = useApi()!;

  return useMutation({
    mutationFn: async (data: SetAgenticNotebookStateRequest) => {
      const response = await api.setAgenticNotebookStateApiV1AgenticNotebooksNotebookIdStatePut(notebookId, data);

      return response.data;
    },
    onSuccess,
    onError,
  });
};
