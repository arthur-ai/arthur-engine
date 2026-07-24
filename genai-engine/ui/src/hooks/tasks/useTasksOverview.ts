import { useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";

import type { TraceOverviewResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export type TasksOverviewMap = Record<string, TraceOverviewResponse>;

export const useTasksOverview = (taskIds: string[], options?: { sinceCreated?: boolean }) => {
  const api = useApi()!;
  const sinceCreated = options?.sinceCreated ?? false;

  return useQuery({
    queryKey: [...queryKeys.tasksOverview.all(taskIds), { sinceCreated }],
    enabled: taskIds.length > 0,
    queryFn: async (): Promise<TasksOverviewMap> => {
      // Default: 7-day window feeds the card metric tiles (traces/tokens/success).
      // sinceCreated: unbounded lookback (epoch -> now) so "Last active" reflects
      // the true most-recent activity, not just the last 7 days.
      let startTime: string;
      if (sinceCreated) {
        startTime = new Date(0).toISOString();
      } else {
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        startTime = sevenDaysAgo.toISOString();
      }

      const response = await api.api.getTracesOverviewApiV1TracesOverviewPost({
        task_ids: taskIds,
        start_time: startTime,
        end_time: new Date().toISOString(),
      });

      const overviews = response.data.overviews || [];
      return Object.fromEntries(overviews.map((overview) => [overview.task_id, overview]));
    },
  });
};
