import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { pollWhileAnyInProgress, POLL_INTERVAL } from "@/lib/polling";
import { queryKeys } from "@/lib/queryKeys";
import { DEFAULT_PAGINATION_PARAMS, PaginationParams } from "@/types/common";

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
    refetchInterval: pollWhileAnyInProgress(
      (data) => data?.data.data,
      (testCase) => testCase.status,
      POLL_INTERVAL.FAST
    ),
  });
};
