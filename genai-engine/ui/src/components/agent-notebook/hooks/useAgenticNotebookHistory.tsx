import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export const agenticNotebookHistoryQueryOptions = ({ api, notebookId }: { api: Api<unknown>; notebookId: string }) =>
  queryOptions({
    queryKey: queryKeys.agentNotebooks.history(notebookId),
    queryFn: () => api.api.getAgenticNotebookHistoryApiV1AgenticNotebooksNotebookIdHistoryGet({ notebookId, page: 0, page_size: 5 }),
    select: (data) => data.data,
  });

export const useAgenticNotebookHistory = (notebookId: string) => {
  const api = useApi()!;

  return useQuery(agenticNotebookHistoryQueryOptions({ api, notebookId }));
};
