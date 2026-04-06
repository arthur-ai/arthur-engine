import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export const agenticNotebookQueryOptions = ({ api, notebookId }: { api: Api<unknown>; notebookId: string }) =>
  queryOptions({
    queryKey: queryKeys.agentNotebooks.byId(notebookId),
    queryFn: () => api.api.getAgenticNotebookApiV1AgenticNotebooksNotebookIdGet(notebookId),
    select: (data) => data.data,
  });

export const useAgenticNotebook = (notebookId: string) => {
  const api = useApi()!;

  return useQuery({ ...agenticNotebookQueryOptions({ api, notebookId }), enabled: !!notebookId });
};
