import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  name: string;
  versions: number[];
};

export const usePromptsVariables = (opts: Opts) => {
  const { task } = useTask();
  const { api } = useApi()!;

  return useQuery({
    queryKey: [...queryKeys.prompts.variables(opts.name, opts.versions)],
    queryFn: async () => {
      const promises = opts.versions.map((version) =>
        api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(opts.name, version.toString(), task!.id)
      );

      const prompts = await Promise.all(promises);
      const variables = new Set(prompts.flatMap((p) => p.data.variables || []));

      return Array.from(variables);
    },
  });
};
