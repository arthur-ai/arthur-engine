import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { DEFAULT_PAGINATION_PARAMS, PaginationParams } from "@/types/common";

export const agentNotebooksQueryOptions = ({
  taskId,
  api,
  pagination = DEFAULT_PAGINATION_PARAMS,
}: {
  taskId: string;
  api: Api<unknown>;
  pagination?: PaginationParams;
}) => {
  return queryOptions({
    queryKey: [queryKeys.agentNotebooks.all(taskId), pagination],
    queryFn: () =>
      api.api.listAgenticNotebooksApiV1TasksTaskIdAgenticNotebooksGet({ taskId, page: pagination.page, page_size: pagination.page_size }),
    select: (data) => data.data,
  });
};

export const useAgentNotebooks = (pagination?: PaginationParams) => {
  const api = useApi()!;
  const { task } = useTask()!;

  return useQuery(agentNotebooksQueryOptions({ taskId: task!.id, api, pagination }));
};
