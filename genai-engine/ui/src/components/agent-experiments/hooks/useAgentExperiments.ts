import { useQuery } from "@tanstack/react-query";

import { AgentExperiment } from "../types";

import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const agentExperimentsQueryOptions = (taskId: string) => {
  return {
    queryKey: queryKeys.agentExperiments.all(taskId),
    queryFn: () => {
      return MOCK_AGENT_EXPERIMENTS;
    },
  };
};

export const useAgentExperiments = () => {
  const { task } = useTask();

  return useQuery(agentExperimentsQueryOptions(task!.id));
};

export const MOCK_AGENT_EXPERIMENTS: AgentExperiment[] = [
  {
    id: "1",
    name: "Agent Experiment 1",
    dataset_id: "1",
    endpoint_id: "1",
    variable_mapping: {},
    runtime_variable_mapping: {},
  },
  {
    id: "2",
    name: "Agent Experiment 2",
    dataset_id: "2",
    endpoint_id: "2",
    variable_mapping: {},
    runtime_variable_mapping: {},
  },
];
