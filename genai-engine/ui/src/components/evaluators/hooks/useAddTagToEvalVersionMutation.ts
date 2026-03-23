import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { LLMEval } from "@/lib/api-client/api-client";

interface AddTagVariables {
  evalName: string;
  evalVersion: string;
  taskId: string;
  data: { tag: string };
}

export function useAddTagToEvalVersionMutation() {
  const api = useApi();

  return useApiMutation<LLMEval, AddTagVariables>({
    mutationFn: async ({ evalName, evalVersion, taskId, data }: AddTagVariables) => {
      if (!api) throw new Error("API not available");

      const response = await api.api.addTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut(
        evalName,
        evalVersion,
        taskId,
        data
      );
      return response.data;
    },
    invalidateQueries: [
      { queryKey: ["getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet"] },
      { queryKey: ["getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet"] },
    ],
  });
}
