import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticExperimentSummary, CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  onSuccess?: (data: AgenticExperimentSummary) => void;
};

export const useCreateNewExperiment = ({ onSuccess }: Opts = {}) => {
  const queryClient = useQueryClient();
  const { task } = useTask();
  const { api } = useApi()!;

  return useMutation({
    mutationFn: async (data: CreateAgenticExperimentRequest) => {
      const response = await api.createAgenticExperimentApiV1TasksTaskIdAgenticExperimentsPost(task!.id, data);

      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agentExperiments.all(task!.id) });
      onSuccess?.(data);
    },
  });
};
