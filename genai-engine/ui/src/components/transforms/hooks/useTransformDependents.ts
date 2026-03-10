import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { ContinuousEvalResponse } from "@/lib/api-client/api-client";

const MAX_PAGE_SIZE = 5000;

export function useTransformDependents(transformId: string | null) {
  const api = useApi();
  const { task } = useTask();
  const taskId = task?.id;

  const query = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: ["transformDependents", taskId, transformId],
    queryFn: async () => {
      if (!api || !taskId) throw new Error("API or task not available");

      const response = await api.api.listContinuousEvalsApiV1TasksTaskIdContinuousEvalsGet({
        taskId,
        page: 0,
        page_size: MAX_PAGE_SIZE,
      });

      const allEvals = response.data.evals ?? [];
      return allEvals.filter((e: ContinuousEvalResponse) => e.transform_id === transformId);
    },
    enabled: !!transformId && !!api && !!taskId,
  });

  return {
    continuousEvals: query.data ?? [],
    isLoading: query.isLoading && !!transformId,
    error: query.error,
  };
}
