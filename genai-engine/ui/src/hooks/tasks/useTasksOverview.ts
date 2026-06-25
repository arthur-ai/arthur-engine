import { useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";

import type { TraceOverviewResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export type TasksOverviewMap = Record<string, TraceOverviewResponse>;

export const useTasksOverview = (taskIds: string[]) => {
  const api = useApi()!;

  return useQuery({
    queryKey: [...queryKeys.tasksOverview.all(taskIds)],
    enabled: taskIds.length > 0,
    queryFn: async (): Promise<TasksOverviewMap> => {
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

      const response = await api.api.getTracesOverviewApiV1TracesOverviewPost({
        task_ids: taskIds,
        start_time: sevenDaysAgo.toISOString(),
        end_time: new Date().toISOString(),
      });

      const overviews = response.data.overviews || [];
      return Object.fromEntries(overviews.map((overview) => [overview.task_id, overview]));
    },
  });
};
