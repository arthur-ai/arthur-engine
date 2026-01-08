import { useMutation } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useNavigate } from "react-router-dom";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";

export const useCreateNewExperiment = () => {
  const { task } = useTask();
  const { api } = useApi()!;
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async (data: CreateAgenticExperimentRequest) => {
      const response = await api.createAgenticExperimentApiV1TasksTaskIdAgenticExperimentsPost(task!.id, data);

      return response.data;
    },
    onSuccess: (data) => {
      enqueueSnackbar(`Experiment with id "${data.id}" created successfully!`, { variant: "success" });
      navigate(`/tasks/${task!.id}/agent-experiments/${data.id}`, { replace: true });
    },
  });
};
