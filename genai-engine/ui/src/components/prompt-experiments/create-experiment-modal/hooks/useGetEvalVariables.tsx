import { useMutation } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

export const useGetEvalVariables = () => {
  const { task } = useTask();
  const { api } = useApi()!;

  const mutation = useMutation({
    mutationFn: async (evals: { name: string; version: number }[]) => {
      const promises = evals.map(({ name, version }) =>
        api.getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet(name, version.toString(), task!.id)
      );

      const evalsData = await Promise.all(promises);
      return evalsData.map(({ data }) => ({
        name: data.name,
        version: data.version,
        variables: data.variables || [],
      }));
    },
  });

  return { getVariables: mutation.mutateAsync, isPending: mutation.isPending };
};
