import { useSnackbar } from "notistack";

import { useAttachExperimentToAgenticNotebook } from "./useAttachExperimentToAgenticNotebook";

import { useCreateNewExperiment } from "@/components/agent-experiments/new/hooks/useCreateNewExperiment";
import { CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";
import { EVENT_NAMES, track } from "@/services/amplitude";

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

      track(EVENT_NAMES.AGENT_NOTEBOOK_EXPERIMENT_RUN, { notebook_id: notebookId, experiment_id: experiment.id });
    },
    loading: createNewExperimentMutation.isPending || attachExperimentToNotebookMutation.isPending,
  };
};
