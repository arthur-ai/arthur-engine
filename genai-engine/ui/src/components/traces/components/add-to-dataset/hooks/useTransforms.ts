import { useQuery } from "@tanstack/react-query";

import { TraceTransform } from "../form/shared";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";


// Fetches transforms for a task
export function useTransforms(datasetId: string | undefined) {
  const api = useApi();
  const { task } = useTask();
  const taskId = task?.id;

  return useQuery({
    queryKey: ["transforms", taskId, api],
    queryFn: async () => {
      if (!taskId || !api) return [];

      try {
        const response = await api.api.listTransformsForTaskApiV1TasksTaskIdTracesTransformsGet({ taskId });
        return (response.data.transforms || []) as TraceTransform[];
      } catch (error: any) {
        if (error.response?.status === 404) return [];
        throw error;
      }
    },
    enabled: !!taskId && !!api && !!datasetId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
