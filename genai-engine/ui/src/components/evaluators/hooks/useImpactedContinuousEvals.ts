import { useCallback } from "react";

import { useApi } from "@/hooks/useApi";
import type { ContinuousEvalResponse } from "@/lib/api-client/api-client";

const MAX_PAGE_SIZE = 5000;

export const useImpactedContinuousEvals = (taskId: string | undefined) => {
  const api = useApi();

  const fetchImpactedCEs = useCallback(
    async (evalName: string, newVersion: number): Promise<ContinuousEvalResponse[]> => {
      if (!api || !taskId) return [];

      const response = await api.api.listContinuousEvalsApiV1TasksTaskIdContinuousEvalsGet({
        taskId,
        llm_eval_name_exact: evalName,
        page_size: MAX_PAGE_SIZE,
      });

      const allCEs = response.data.evals ?? [];
      return allCEs.filter((ce) => (ce.llm_eval_version ?? 0) < newVersion);
    },
    [api, taskId]
  );

  return { fetchImpactedCEs };
};
