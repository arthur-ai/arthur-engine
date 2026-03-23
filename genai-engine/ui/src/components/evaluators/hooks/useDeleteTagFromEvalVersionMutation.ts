import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";

interface DeleteTagVariables {
  evalName: string;
  evalVersion: string;
  tag: string;
  taskId: string;
}

export function useDeleteTagFromEvalVersionMutation() {
  const api = useApi();

  return useApiMutation<void, DeleteTagVariables>({
    mutationFn: async ({ evalName, evalVersion, tag, taskId }: DeleteTagVariables) => {
      if (!api) throw new Error("API not available");

      await api.api.deleteTagFromLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsTagDelete(evalName, evalVersion, tag, taskId);
    },
    invalidateQueries: [
      { queryKey: ["getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet"] },
      { queryKey: ["getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet"] },
    ],
  });
}
