import { useMutation, useQueryClient } from "@tanstack/react-query";
import { enqueueSnackbar } from "notistack";
import { useNavigate } from "react-router-dom";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";

export const useDeleteAgentExperiment = () => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;
  const { task } = useTask();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async (experimentId: string) => {
      if (!api) throw new Error("API not available");
      await api.deleteAgenticExperimentApiV1AgenticExperimentsExperimentIdDelete(experimentId);
    },
    onSuccess: async (_, experimentId) => {
      track(EVENT_NAMES.AGENT_EXPERIMENT_DELETED, { experiment_id: experimentId });
      await queryClient.invalidateQueries({ queryKey: [queryKeys.agentExperiments.all(task!.id)] });
      enqueueSnackbar("Experiment deleted successfully", { variant: "success" });
      navigate(`/tasks/${task!.id}/agent-experiments`);
    },
    onError: () => {
      enqueueSnackbar("Failed to delete experiment", { variant: "error" });
    },
  });
};
