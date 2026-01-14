import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const useDeleteAgenticNotebook = () => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;
  const { task } = useTask();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.deleteAgenticNotebookApiV1AgenticNotebooksNotebookIdDelete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agentNotebooks.all(task!.id) });
      enqueueSnackbar("Notebook deleted successfully", { variant: "success" });
    },
    onError: () => {
      enqueueSnackbar("Failed to delete notebook", { variant: "error" });
    },
  });
};
