import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

export const usePollExperiment = (experimentId?: string) => {
  const { api } = useApi()!;

  return useQuery({
    enabled: !!experimentId,
    queryKey: [queryKeys.agentExperiments.testCases(experimentId!)],
    queryFn: () => api.getAgenticExperimentTestCasesApiV1AgenticExperimentsExperimentIdTestCasesGet({ experimentId: experimentId! }),
    select: (data) => data.data,
    refetchInterval: (query) => {
      return query.state.data?.data.data.some((testCase) => ["queued", "running"].includes(testCase.status)) ? 1000 : false;
    },
  });
};
