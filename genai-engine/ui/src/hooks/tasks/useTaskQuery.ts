import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";

import type { Api, TaskResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const taskQueryOptions = ({ api, taskId }: { api: Api<unknown>; taskId: string }) =>
  queryOptions({
    queryKey: queryKeys.tasks.byId(taskId),
    queryFn: async (): Promise<TaskResponse> => {
      const response = await api.api.getTaskApiV2TasksTaskIdGet(taskId);
      return response.data;
    },
    staleTime: 30000,
  });

export function useTaskQuery(taskId: string) {
  const api = useApi();

  return useQuery({
    ...taskQueryOptions({ api: api!, taskId }),
    enabled: !!api && !!taskId,
  });
}
