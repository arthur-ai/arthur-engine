import { useDebouncedCallback } from "@tanstack/react-pacer";
import { useSnackbar } from "notistack";

import { useExperimentStore } from "../stores/experiment.store";
import { usePromptPlaygroundStore } from "../stores/playground.store";
import { serializePlaygroundState } from "../utils/notebookStateUtils";

import { useSetNotebookStateMutation } from "@/hooks/useNotebooks";

type Props = {
  notebookId: string;
  enabled: boolean;
};

export const useAutosave = ({ notebookId, enabled }: Props) => {
  const { enqueueSnackbar } = useSnackbar();

  const actions = usePromptPlaygroundStore((state) => state.actions);

  const mutation = useSetNotebookStateMutation(() => {
    enqueueSnackbar("Notebook saved", { variant: "success" });
  });

  const debouncer = useDebouncedCallback(
    async () => {
      const { prompts } = usePromptPlaygroundStore.getState();
      const { experimentConfig } = useExperimentStore.getState();
      const serializedState = serializePlaygroundState({ prompts }, experimentConfig);

      actions.resetMutation();

      await mutation.mutateAsync({
        notebookId,
        request: { state: serializedState },
      });
    },
    {
      wait: 5000,
      enabled,
    }
  );

  return [debouncer, mutation.isPending] as const;
};
