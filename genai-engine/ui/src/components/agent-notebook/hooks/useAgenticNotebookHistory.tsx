import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { DEFAULT_PAGINATION_PARAMS, PaginationParams } from "@/types/common";

export const agenticNotebookHistoryQueryOptions = ({
  api,
  notebookId,
  pagination = DEFAULT_PAGINATION_PARAMS,
}: {
  api: Api<unknown>;
  notebookId: string;
  pagination?: PaginationParams;
}) =>
  queryOptions({
    queryKey: [queryKeys.agentNotebooks.history(notebookId), pagination],
    queryFn: () => api.api.getAgenticNotebookHistoryApiV1AgenticNotebooksNotebookIdHistoryGet({ notebookId, ...pagination }),
    select: (data) => data.data,
  });

export const useAgenticNotebookHistory = (notebookId: string, pagination?: PaginationParams) => {
  const api = useApi()!;

  return useQuery(agenticNotebookHistoryQueryOptions({ api, notebookId, pagination }));
};
