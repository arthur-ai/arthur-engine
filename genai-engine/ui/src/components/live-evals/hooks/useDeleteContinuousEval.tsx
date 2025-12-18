import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { useSnackbar } from "notistack";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const useDeleteContinuousEval = () => {
  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  const { task } = useTask();

  return useMutation({
    mutationFn: async (evalId: string) => {
      await api.api.deleteContinuousEvalApiV1ContinuousEvalsEvalIdDelete(evalId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [queryKeys.continuousEvals.all(task!.id)] });
      enqueueSnackbar("Continuous eval deleted successfully", { variant: "success" });
    },
    onError: (error) => {
      let message = "Failed to delete continuous eval";

      if (error instanceof AxiosError) {
        message = error.response?.data.detail ?? message;
      }

      enqueueSnackbar(message, { variant: "error" });
    },
  });
};
