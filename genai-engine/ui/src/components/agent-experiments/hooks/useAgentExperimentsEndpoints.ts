import { useQuery } from "@tanstack/react-query";

import type { AgentExperimentEndpoint } from "../types";

import { queryKeys } from "@/lib/queryKeys";
import { wait } from "@/utils";

export const agentExperimentsEndpointsQueryOptions = () => {
  return {
    queryKey: queryKeys.agentExperiments.endpoints.all(),
    queryFn: async () => {
      await wait(500);

      return MOCK_AGENT_EXPERIMENTS_ENDPOINTS;
    },
  };
};

export const useAgentExperimentsEndpoints = () => {
  return useQuery(agentExperimentsEndpointsQueryOptions());
};

const MOCK_AGENT_EXPERIMENTS_ENDPOINTS: AgentExperimentEndpoint[] = [
  {
    name: "Mastra Agent",
    url: "https://api.mastra.ai/v1/agent",
    headers: {},
    body: "",
  },
  {
    name: "Mastra Agent",
    url: "https://api.upsolve.ai/v1/api/chat-mastra",
    headers: {},
    body: JSON.stringify({
      messages: [{ role: "user", content: "{{question}}" }],
    }),
  },
];
