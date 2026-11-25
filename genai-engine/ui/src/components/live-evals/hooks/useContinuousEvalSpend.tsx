import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

export const useContinuousEvalSpend = (evalId?: string) => {
  const api = useApi()!;

  return useQuery({
    enabled: !!evalId,
    queryKey: [queryKeys.continuousEvals.spend(evalId!)],
    queryFn: () => api.api.getContinuousEvalSpendApiV1ContinuousEvalsEvalIdSpendGet(evalId!),
    select: (data) => data.data,
  });
};

export const useContinuousEvalSpendEstimate = (taskId?: string, llmEvalName?: string | null, sampleRate?: number | null) => {
  const api = useApi()!;

  return useQuery({
    // undefined means the sample rate field is invalid, so there is nothing to estimate
    enabled: !!taskId && !!llmEvalName && sampleRate !== undefined,
    queryKey: [queryKeys.continuousEvals.spendEstimate(taskId!, llmEvalName!, sampleRate ?? null)],
    queryFn: () =>
      api.api.estimateContinuousEvalSpendApiV1TasksTaskIdContinuousEvalsSpendEstimateGet({
        taskId: taskId!,
        llm_eval_name: llmEvalName!,
        sample_rate: sampleRate ?? undefined,
      }),
    select: (data) => data.data,
  });
};
