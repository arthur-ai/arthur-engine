import { useQuery } from "@tanstack/react-query";

import { MOCK_AGENT_EXPERIMENTS_ENDPOINTS } from "./useAgentExperimentsEndpoints";

import { queryKeys } from "@/lib/queryKeys";

export const agentExperimentEndpointQueryOptions = (endpointId: string) => {
  return {
    queryKey: queryKeys.agentExperiments.endpoints.byId(endpointId),
    queryFn: () => {
      return MOCK_AGENT_EXPERIMENTS_ENDPOINTS.find((endpoint) => endpoint.id === endpointId);
    },
  };
};

export const useAgentExperimentEndpoint = (endpointId: string) => {
  return useQuery(agentExperimentEndpointQueryOptions(endpointId));
};
