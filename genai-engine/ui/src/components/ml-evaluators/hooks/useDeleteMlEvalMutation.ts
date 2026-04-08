import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { useSnackbar } from "notistack";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { encodePathParam } from "@/utils/url";

export const useDeleteMlEvalMutation = (onSuccess?: () => void) => {
  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  const { task } = useTask();

  return useMutation({
    mutationFn: async (evalName: string) => {
      await api.api.deleteMlEvalApiV2TasksTaskIdMlEvalsEvalNameDelete(encodePathParam(evalName), task!.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["getAllMlEvalsApiV2TasksTaskIdMlEvalsGet"] });
      enqueueSnackbar("ML eval deleted successfully", { variant: "success" });
      onSuccess?.();
    },
    onError: (error) => {
      let message = "Failed to delete ML eval";
      if (error instanceof AxiosError) {
        message = error.response?.data.detail ?? message;
      }
      enqueueSnackbar(message, { variant: "error" });
    },
  });
};
