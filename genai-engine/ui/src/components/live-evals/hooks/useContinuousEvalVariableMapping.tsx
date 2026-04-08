import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

export const useContinuousEvalVariableMapping = (taskId?: string, transformId?: string, evalName?: string, evalVersion?: string) => {
  const api = useApi()!;

  return useQuery({
    enabled: !!taskId && !!transformId && !!evalName && !!evalVersion,
    queryKey: [queryKeys.continuousEvals.variableMapping(taskId!, transformId!, evalName!, evalVersion!)],
    queryFn: () =>
      api.api.getContinuousEvalVariablesAndMappingsApiV1TasksTaskIdContinuousEvalsTransformsTransformIdLlmEvalsEvalNameVersionsEvalVersionVariablesGet({
        transformId: transformId!,
        evalName: evalName!,
        evalVersion: evalVersion!,
        taskId: taskId!,
      }),
    select: (data) => data.data,
  });
};
