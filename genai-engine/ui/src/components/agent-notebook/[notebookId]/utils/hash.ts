import { digest, serialize } from "ohash";

import { AgentNotebookStateFormData } from "../form";

export const hashFormState = (state: AgentNotebookStateFormData) => {
  return digest(serialize(state));
};
