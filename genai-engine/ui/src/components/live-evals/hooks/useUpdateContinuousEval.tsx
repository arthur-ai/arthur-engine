import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useSnackbar } from "notistack";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { UpdateContinuousEvalRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useUpdateContinuousEval = (evalId: string) => {
  const api = useApi()!;
  const { task } = useTask();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: async (data: UpdateContinuousEvalRequest) => {
      return api.api.updateContinuousEvalApiV1ContinuousEvalsEvalIdPatch(evalId, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [queryKeys.continuousEvals.all(task!.id)] });
      queryClient.invalidateQueries({ queryKey: [queryKeys.continuousEvals.byId(evalId)] });
      enqueueSnackbar("Continuous eval updated successfully", { variant: "success" });
    },
    onError: (error) => {
      let message = "Failed to update continuous eval";

      if (isAxiosError(error)) {
        message = error.response?.data.detail ?? message;
      }

      enqueueSnackbar(message, { variant: "error" });
    },
  });
};
