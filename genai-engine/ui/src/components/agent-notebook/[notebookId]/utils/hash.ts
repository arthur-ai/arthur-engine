import { digest, serialize } from "ohash";

import { AgentNotebookStateFormData } from "../form";

export const hashFormState = (state: AgentNotebookStateFormData) => {
  // Exclude requestTimeParameters from the hash — they are ephemeral/sensitive
  // values that must not trigger autosave or the "Edited" indicator.
  const { requestTimeParameters: _, ...persistableState } = state;
  return digest(serialize(persistableState));
};
