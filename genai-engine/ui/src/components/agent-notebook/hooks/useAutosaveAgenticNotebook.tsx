import { useAsyncDebouncer } from "@tanstack/react-pacer";
import { useSnackbar } from "notistack";

import { AgentNotebookStateFormData } from "../[notebookId]/form";
import { useMetaStore } from "../[notebookId]/store/meta.store";
import { hashFormState } from "../[notebookId]/utils/hash";
import { mapFormToRequest, mapTemplateToForm } from "../[notebookId]/utils/mapper";

import { useSaveAgenticNotebookState } from "./useSaveAgenticNotebookState";

export const useAutosaveAgenticNotebook = (notebookId: string) => {
  const { enqueueSnackbar } = useSnackbar();

  const actions = useMetaStore((state) => state.actions);

  const saveAgenticNotebookStateMutation = useSaveAgenticNotebookState(notebookId, {
    onSuccess: async (data) => {
      actions.setBaseline(hashFormState(mapTemplateToForm(data.state)));
      enqueueSnackbar(`Notebook state autosaved!`, { variant: "success" });
    },
    onError: () => {
      enqueueSnackbar(`Couldn't autosave notebook state. Review your configuration and try again.`, { variant: "error" });
    },
  });

  const autosave = useAsyncDebouncer(
    async (state: AgentNotebookStateFormData) => {
      await saveAgenticNotebookStateMutation.mutateAsync(mapFormToRequest(state));
    },
    { wait: 5000 },
    (state) => state.isExecuting
  );

  return {
    save: autosave.maybeExecute,
    cancel: () => {
      autosave.abort();
      autosave.cancel();
    },
    forceSave: autosave.flush,
    isSaving: autosave.state,
  };
};
