import { useQuery } from "@tanstack/react-query";

import { agentExperimentQueryOptions } from "../../hooks/useAgentExperiment";

import { useApi } from "@/hooks/useApi";
import { ExperimentStatus } from "@/lib/api-client/api-client";

const POLL_STATUSES: Set<ExperimentStatus> = new Set(["running", "queued"] satisfies readonly ExperimentStatus[]);

export const usePollAgentExperiment = (experimentId?: string) => {
  const api = useApi()!;

  return useQuery({
    ...agentExperimentQueryOptions({ api, experimentId }),
    refetchInterval: (query) => {
      const status = query.state.data?.data.status;
      return status && POLL_STATUSES.has(status) ? 1000 : false;
    },
  });
};
