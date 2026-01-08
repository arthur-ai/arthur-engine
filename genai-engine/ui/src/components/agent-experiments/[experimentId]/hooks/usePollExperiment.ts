import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { TestCaseStatus } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

const POLL_STATUSES: Set<TestCaseStatus> = new Set(["queued", "running", "evaluating"] satisfies readonly TestCaseStatus[]);

export const usePollExperiment = (experimentId?: string) => {
  const { api } = useApi()!;

  return useQuery({
    enabled: !!experimentId,
    queryKey: [queryKeys.agentExperiments.testCases(experimentId!)],
    queryFn: () => api.getAgenticExperimentTestCasesApiV1AgenticExperimentsExperimentIdTestCasesGet({ experimentId: experimentId! }),
    select: (data) => data.data,
    refetchInterval: (query) => {
      return query.state.data?.data.data.some((testCase) => POLL_STATUSES.has(testCase.status)) ? 1000 : false;
    },
  });
};
