import { useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";

import { queryKeys } from "@/lib/queryKeys";

export const useTaskMetrics = (taskId: string) => {
  const api = useApi()!;

  return useQuery({
    queryKey: [...queryKeys.taskMetrics.all(taskId)],
    queryFn: async () => {
      try {
        // Get traces from last 7 days
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        const response = await api.api.listTracesMetadataApiV1TracesGet({
          task_ids: [taskId],
          start_time: sevenDaysAgo.toISOString(),
          page_size: 5000, // Get all traces for accurate metrics
          page: 0,
        });

        const traces = response.data.traces || [];
        const traceCount = response.data.count || 0;

        // Calculate total tokens
        const totalTokens = traces.reduce((sum, trace) => {
          return sum + (trace.total_token_count || 0);
        }, 0);

        // Calculate success rate (traces without errors)
        // We'll consider a trace successful if it completed (has end_time)
        const successfulTraces = traces.filter((trace) => trace.end_time).length;
        const successRate = traceCount > 0 ? Math.round((successfulTraces / traceCount) * 100) : 0;

        // Find the most recent trace end_time for last active
        let lastActive: string | null = null;
        if (traces.length > 0) {
          for (const trace of traces) {
            const traceDate = trace.end_time || trace.created_at;
            if (traceDate) {
              if (!lastActive || new Date(traceDate) > new Date(lastActive)) {
                lastActive = traceDate;
              }
            }
          }
        }

        return { traceCount, totalTokens, successRate, lastActive };
      } catch (err) {
        console.error(`Failed to fetch metrics for task ${taskId}:`, err);
        return { traceCount: 0, totalTokens: 0, successRate: 0, lastActive: null };
      }
    },
  });
};
