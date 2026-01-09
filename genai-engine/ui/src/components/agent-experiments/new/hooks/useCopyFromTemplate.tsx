import { parseAsString, useQueryState } from "nuqs";

import { useAgentExperiment } from "../../hooks/useAgentExperiment";

export const useCopyFromTemplate = () => {
  const [template] = useQueryState("template", parseAsString);

  return useAgentExperiment(template ?? undefined);
};
