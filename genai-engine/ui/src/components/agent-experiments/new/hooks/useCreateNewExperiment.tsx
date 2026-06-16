import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticExperimentSummary, CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { track } from "@/services/analytics";

type Opts = {
  onSuccess?: (data: AgenticExperimentSummary) => void;
};

export const useCreateNewExperiment = ({ onSuccess }: Opts = {}) => {
  const queryClient = useQueryClient();
  const { task } = useTask();
  const { api } = useApi()!;

  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: async (data: CreateAgenticExperimentRequest) => {
      const response = await api.createAgenticExperimentApiV1TasksTaskIdAgenticExperimentsPost(task!.id, data);

      return response.data;
    },
    onSuccess: (data) => {
      track("agent_experiment/created", { experiment_id: data.id });
      queryClient.invalidateQueries({ queryKey: [queryKeys.agentExperiments.all(task!.id)] });
      onSuccess?.(data);
    },
    onError: () => {
      enqueueSnackbar("Failed to create experiment. Please check the form and try again.", { variant: "error" });
    },
  });
};
