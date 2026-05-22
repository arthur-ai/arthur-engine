import { useCallback } from "react";

import { useApi } from "@/hooks/useApi";
import type { ContinuousEvalResponse } from "@/lib/api-client/api-client";

const MAX_PAGE_SIZE = 5000;

export const useImpactedTransformContinuousEvals = (taskId: string | undefined) => {
  const api = useApi();

  const fetchImpactedCEs = useCallback(
    async (transformId: string): Promise<ContinuousEvalResponse[]> => {
      if (!api || !taskId) return [];

      const dependentsResponse = await api.api.getTransformDependentsApiV1TracesTransformsTransformIdDependentsGet(transformId);
      const ceIds = dependentsResponse.data.continuous_evals?.map((ce) => ce.id) ?? [];

      if (ceIds.length === 0) return [];

      const cesResponse = await api.api.listContinuousEvalsApiV1TasksTaskIdContinuousEvalsGet({
        taskId,
        continuous_eval_ids: ceIds,
        page_size: MAX_PAGE_SIZE,
      });

      return cesResponse.data.evals ?? [];
    },
    [api, taskId]
  );

  return { fetchImpactedCEs };
};
