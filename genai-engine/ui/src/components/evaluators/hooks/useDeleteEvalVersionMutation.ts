import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";

export const useDeleteEvalVersionMutation = (
  taskId: string | undefined,
  evalName: string,
  onSuccess?: () => void
) => {
  const api = useApi();

  return useApiMutation<void, number>({
    mutationFn: async (version: number) => {
      if (!api || !taskId) throw new Error("API or task not available");

      await api.api.softDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDelete(
        evalName,
        version.toString(),
        taskId
      );
    },
    invalidateQueries: [{ queryKey: ["getLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet"] }],
    onSuccess,
    onError: (err) => {
      console.error("Failed to delete eval version:", err);
    },
  });
};
