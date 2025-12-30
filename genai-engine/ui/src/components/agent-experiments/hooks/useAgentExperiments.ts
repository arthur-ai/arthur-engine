import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const useAgentExperiments = () => {
  const { api } = useApi()!;
  const { task } = useTask();

  return useQuery({
    queryKey: queryKeys.agentExperiments.all(task!.id),
    queryFn: () => {
      return [];
    },
  });
};

const MOCK_AGENT_EXPERIMENTS = [];
