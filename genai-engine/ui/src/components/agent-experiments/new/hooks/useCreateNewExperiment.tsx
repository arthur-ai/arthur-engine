import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";

import { useOutOfCreditsDialog } from "@/contexts/OutOfCreditsContext";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import {
  getTokenLimitDetail,
  isTokenLimitExceededError,
} from "@/lib/api-errors";
import { AgenticExperimentSummary, CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";

type Opts = {
  onSuccess?: (data: AgenticExperimentSummary) => void;
};

export const useCreateNewExperiment = ({ onSuccess }: Opts = {}) => {
  const queryClient = useQueryClient();
  const { task } = useTask();
  const { api } = useApi()!;

  const { enqueueSnackbar } = useSnackbar();
  const { show: showOutOfCredits } = useOutOfCreditsDialog();

  return useMutation({
    mutationFn: async (data: CreateAgenticExperimentRequest) => {
      const response = await api.createAgenticExperimentApiV1TasksTaskIdAgenticExperimentsPost(task!.id, data);

      return response.data;
    },
    onSuccess: (data) => {
      track(EVENT_NAMES.AGENT_EXPERIMENT_CREATED, { experiment_id: data.id });
      queryClient.invalidateQueries({ queryKey: [queryKeys.agentExperiments.all(task!.id)] });
      onSuccess?.(data);
    },
    onError: (error) => {
      // UP-4390: route 402 quota errors to the global dialog before falling
      // back to the generic snackbar.
      if (isTokenLimitExceededError(error)) {
        showOutOfCredits(getTokenLimitDetail(error));
        return;
      }
      enqueueSnackbar("Failed to create experiment. Please check the form and try again.", { variant: "error" });
    },
  });
};
