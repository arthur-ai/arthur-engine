import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export const agentNotebooksQueryOptions = ({ taskId, api }: { taskId: string; api: Api<unknown> }) => {
  return queryOptions({
    queryKey: queryKeys.agentNotebooks.all(taskId),
    queryFn: () => api.api.listAgenticNotebooksApiV1TasksTaskIdAgenticNotebooksGet({ taskId }),
    select: (data) => data.data,
  });
};

export const useAgentNotebooks = () => {
  const api = useApi()!;
  const { task } = useTask()!;

  return useQuery(agentNotebooksQueryOptions({ taskId: task!.id, api }));
};
