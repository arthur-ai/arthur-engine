import { useQuery } from "@tanstack/react-query";

import { TraceTransform } from "../types";

import { useApi } from "@/hooks/useApi";

// Fetches transforms for a task, returns empty array if none exist
export function useTransforms(taskId: string | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["transforms", taskId, api],
    queryFn: async () => {
      if (!taskId || !api) return [];

      try {
        const response = await api.api.listTransformsForTaskApiV1TasksTaskIdTracesTransformsGet({ taskId });
        return (response.data.transforms || []) as TraceTransform[];
      } catch (error: unknown) {
        if (error && typeof error === 'object' && 'response' in error) {
          const apiError = error as { response?: { status?: number } };
          if (apiError.response?.status === 404) return [];
        }
        throw error;
      }
    },
    enabled: !!taskId && !!api,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
