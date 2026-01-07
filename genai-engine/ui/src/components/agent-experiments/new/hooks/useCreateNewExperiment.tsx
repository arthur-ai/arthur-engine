import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";
import { useMutation } from "@tanstack/react-query";
import { useSnackbar } from "notistack";

export const useCreateNewExperiment = () => {
  const { task } = useTask();
  const { api } = useApi()!;
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: async (data: CreateAgenticExperimentRequest) => {
      const response = await api.createAgenticExperimentApiV1TasksTaskIdAgenticExperimentsPost(task!.id, data);

      return response.data;
    },
    onSuccess: (data) => {
      enqueueSnackbar(`Experiment with id "${data.id}" created successfully!`, { variant: "success" });
    },
  });
};
