import { queryOptions, useQuery } from "@tanstack/react-query";

import { AgentExperiment } from "../types";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export const agentExperimentsQueryOptions = ({ taskId, api }: { taskId: string; api: Api<unknown> }) => {
  return queryOptions({
    queryKey: queryKeys.agentExperiments.all(taskId),
    queryFn: () => api.api.listAgenticExperimentsApiV1TasksTaskIdAgenticExperimentsGet({ taskId }),
    select: (data) => data.data,
  });
};

export const useAgentExperiments = () => {
  const api = useApi()!;
  const { task } = useTask();

  return useQuery(agentExperimentsQueryOptions({ taskId: task!.id, api }));
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
