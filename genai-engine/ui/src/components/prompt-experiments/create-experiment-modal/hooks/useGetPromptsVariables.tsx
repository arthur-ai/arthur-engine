import { useMutation } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

export const useGetPromptsVariables = () => {
  const { task } = useTask();
  const { api } = useApi()!;

  const mutation = useMutation({
    mutationFn: async ({ name, versions }: { name: string; versions: number[] }) => {
      const promises = versions.map((version) =>
        api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(name, version.toString(), task!.id)
      );

      const prompts = await Promise.all(promises);
      const variables = new Set(prompts.flatMap((p) => p.data.variables || []));

      return Array.from(variables);
    },
  });

  return { getVariables: mutation.mutateAsync, isPending: mutation.isPending };
};
