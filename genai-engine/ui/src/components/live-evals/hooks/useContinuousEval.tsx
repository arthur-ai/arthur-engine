import { useQuery } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { useSnackbar } from "notistack";
import { useNavigate } from "react-router-dom";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const useContinuousEval = (evalId?: string) => {
  const api = useApi()!;
  const { task } = useTask();
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();

  return useQuery({
    enabled: !!evalId,
    queryKey: [queryKeys.continuousEvals.byId(evalId!)],
    queryFn: async () => {
      try {
        const response = await api.api.getContinuousEvalByIdApiV1ContinuousEvalsEvalIdGet(evalId!);

        return response;
      } catch (error) {
        if (error instanceof AxiosError) {
          enqueueSnackbar(error.response?.data.detail ?? "Failed to fetch continuous eval", { variant: "error" });
        }

        navigate(`/tasks/${task?.id}/continuous-evals`);

        throw error;
      }
    },
    select: (data) => data.data,
  });
};
