import { useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";

import { queryKeys } from "@/lib/queryKeys";

const ACTIVITY_WINDOW_DAYS = 30;

/**
 * Bulk-fetches the most recent trace activity for a list of tasks.
 * Returns a map of taskId → last active timestamp (ms) for use in sort/filter logic.
 */
export const useAllTasksActivity = (taskIds: string[]) => {
  const api = useApi()!;

  return useQuery({
    queryKey: queryKeys.allTasksActivity.all(taskIds),
    queryFn: async (): Promise<Record<string, number>> => {
      if (taskIds.length === 0) return {};

      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - ACTIVITY_WINDOW_DAYS);

      const response = await api.api.listTracesMetadataApiV1TracesGet({
        task_ids: taskIds,
        start_time: cutoff.toISOString(),
        page_size: 1000,
        page: 0,
      });

      const traces = response.data.traces || [];
      const activityMap: Record<string, number> = {};

      for (const trace of traces) {
        const traceDate = trace.end_time || trace.start_time || trace.created_at;
        if (!traceDate) continue;

        const ms = new Date(traceDate).getTime();
        if (isNaN(ms)) continue;

        const existing = activityMap[trace.task_id];
        if (existing === undefined || ms > existing) {
          activityMap[trace.task_id] = ms;
        }
      }

      return activityMap;
    },
    enabled: taskIds.length > 0,
  });
};
