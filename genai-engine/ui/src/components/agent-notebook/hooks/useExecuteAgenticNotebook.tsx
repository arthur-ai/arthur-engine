import { useSnackbar } from "notistack";

import { useAttachExperimentToAgenticNotebook } from "./useAttachExperimentToAgenticNotebook";

import { useCreateNewExperiment } from "@/components/agent-experiments/new/hooks/useCreateNewExperiment";
import { CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";
import { track } from "@/services/analytics";

export const useExecuteAgenticNotebook = (notebookId: string) => {
  const { enqueueSnackbar } = useSnackbar();
  const createNewExperimentMutation = useCreateNewExperiment();
  const attachExperimentToNotebookMutation = useAttachExperimentToAgenticNotebook(notebookId);

  return {
    execute: async (data: CreateAgenticExperimentRequest) => {
      const experiment = await createNewExperimentMutation.mutateAsync(data);

      enqueueSnackbar(`Experiment "${experiment.name}" created successfully!`, { variant: "success" });

      await attachExperimentToNotebookMutation.mutateAsync(experiment.id);

      enqueueSnackbar(`Experiment "${experiment.name}" attached to notebook successfully!`, { variant: "success" });

      track("agent_notebook/experiment_run", { notebook_id: notebookId, experiment_id: experiment.id });

      return experiment.id;
    },
    loading: createNewExperimentMutation.isPending || attachExperimentToNotebookMutation.isPending,
  };
};
