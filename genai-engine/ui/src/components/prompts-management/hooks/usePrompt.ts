import { useApiQuery } from "@/hooks/useApiQuery";
import type { AgenticPrompt } from "@/lib/api-client/api-client";

// Get a prompt by name and version
export function usePrompt(taskId: string | undefined, promptName: string | undefined, promptVersion: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet">({
    method: "getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet",
    args: [promptName!, promptVersion!, taskId!],
    enabled: !!taskId && !!promptName && !!promptVersion,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  });

  return {
    prompt: data as AgenticPrompt | undefined,
    error,
    isLoading,
    refetch,
  };
}
