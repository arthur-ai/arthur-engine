import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { DEFAULT_PAGINATION_PARAMS, PaginationParams } from "@/types/common";

export const agentExperimentsQueryOptions = ({
  taskId,
  api,
  pagination = DEFAULT_PAGINATION_PARAMS,
}: {
  taskId: string;
  api: Api<unknown>;
  pagination?: PaginationParams;
}) => {
  return queryOptions({
    queryKey: [queryKeys.agentExperiments.all(taskId), pagination],
    queryFn: () =>
      api.api.listAgenticExperimentsApiV1TasksTaskIdAgenticExperimentsGet({ taskId, page: pagination.page, page_size: pagination.page_size }),
    select: (data) => data.data,
  });
};

export const useAgentExperiments = (pagination: PaginationParams = DEFAULT_PAGINATION_PARAMS) => {
  const api = useApi()!;
  const { task } = useTask();

  return useQuery(agentExperimentsQueryOptions({ taskId: task!.id, api, pagination }));
};
