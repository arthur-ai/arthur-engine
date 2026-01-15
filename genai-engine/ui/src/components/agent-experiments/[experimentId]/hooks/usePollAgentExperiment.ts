import { useQuery } from "@tanstack/react-query";

import { agentExperimentQueryOptions } from "../../hooks/useAgentExperiment";

import { useApi } from "@/hooks/useApi";
import { pollWhileInProgress, POLL_INTERVAL } from "@/lib/polling";

export const usePollAgentExperiment = (experimentId?: string) => {
  const api = useApi()!;

  return useQuery({
    ...agentExperimentQueryOptions({ api, experimentId }),
    refetchInterval: pollWhileInProgress((data) => data?.data.status, POLL_INTERVAL.FAST),
  });
};
