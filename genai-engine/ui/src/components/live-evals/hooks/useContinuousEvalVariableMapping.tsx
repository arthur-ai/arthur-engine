import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

export const useContinuousEvalVariableMapping = (
  taskId?: string,
  transformId?: string,
  evalName?: string,
  evalVersion?: string,
  evalType?: string | null
) => {
  const isML = evalType === "ml";
  const api = useApi()!;

  return useQuery({
    enabled: !!taskId && !!transformId && !!evalName && !!evalVersion && !isML,
    queryKey: [queryKeys.continuousEvals.variableMapping(taskId!, transformId!, evalName!, evalVersion!)],
    queryFn: () =>
      api.api.getContinuousEvalVariablesAndMappingsApiV1TasksTaskIdContinuousEvalsTransformsTransformIdLlmEvalsEvalNameVersionsEvalVersionVariablesGet(
        transformId!,
        evalName!,
        evalVersion!,
        taskId!,
      ),
    select: (data) => data.data,
  });
};
