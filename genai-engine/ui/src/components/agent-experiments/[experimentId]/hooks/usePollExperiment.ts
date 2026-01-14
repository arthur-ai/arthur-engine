import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { TestCaseStatus } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { DEFAULT_PAGINATION_PARAMS, PaginationParams } from "@/types/common";

const POLL_STATUSES: Set<TestCaseStatus> = new Set(["queued", "running", "evaluating"] satisfies readonly TestCaseStatus[]);

export const usePollExperiment = (experimentId?: string, pagination: PaginationParams = DEFAULT_PAGINATION_PARAMS) => {
  const { api } = useApi()!;

  return useQuery({
    enabled: !!experimentId,
    queryKey: [queryKeys.agentExperiments.testCases(experimentId!), pagination],
    queryFn: () =>
      api.getAgenticExperimentTestCasesApiV1AgenticExperimentsExperimentIdTestCasesGet({
        experimentId: experimentId!,
        page: pagination.page,
        page_size: pagination.page_size,
        sort: "desc",
      }),
    select: (data) => data.data,
    placeholderData: keepPreviousData,
    refetchInterval: (query) => {
      return query.state.data?.data.data.some((testCase) => POLL_STATUSES.has(testCase.status)) ? 1000 : false;
    },
  });
};
