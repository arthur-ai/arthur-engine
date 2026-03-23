import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export const agentExperimentQueryOptions = ({ api, experimentId }: { api: Api<unknown>; experimentId?: string }) => {
  return queryOptions({
    enabled: !!experimentId,
    queryKey: queryKeys.agentExperiments.byId(experimentId!),
    queryFn: () => api.api.getAgenticExperimentApiV1AgenticExperimentsExperimentIdGet(experimentId!),
    select: (data) => data.data,
  });
};

export const useAgentExperiment = (experimentId?: string) => {
  const api = useApi()!;

  return useQuery(agentExperimentQueryOptions({ api, experimentId }));
};
