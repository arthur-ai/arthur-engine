import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApi } from "./useApi";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { TaskAnalyticsBucketSize } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { getTimeWindowAndBucketing, TimeInterval } from "@/utils/timeWindows";

export interface TimeSeriesDataPoint {
  timestamp: string;
  tracesCount: number;
  tokens: number;
  cost: number;
  successRate: number;
}

export interface TaskOverviewMetrics {
  tracesCount: number;
  totalTokens: number;
  totalCost: number;
  evalsCount: number;
  successRate: number;
  timeSeriesData: TimeSeriesDataPoint[];
  xLabelFormat: "time" | "date";
  tickStep: number;
}

interface UseTaskOverviewMetricsParams {
  taskId: string;
  interval: TimeInterval;
}

export const useTaskOverviewMetrics = ({ taskId, interval }: UseTaskOverviewMetricsParams) => {
  const api = useApi()!;
  const { timezone } = useDisplaySettings();

  return useQuery({
    queryKey: queryKeys.metrics.overview(taskId, interval, timezone),
    enabled: !!taskId,
    queryFn: async (): Promise<TaskOverviewMetrics> => {
      const queryTime = new Date();
      const timeWindow = getTimeWindowAndBucketing(interval, queryTime, { timezone });

      const startTime = timeWindow.start.toISOString();
      const endTime = timeWindow.end.toISOString();
      const bucketSize = timeWindow.bucketSize as TaskAnalyticsBucketSize;

      const [overviewResponse, timeseriesResponse] = await Promise.all([
        api.api.getTracesOverviewApiV1TracesOverviewPost({
          task_ids: [taskId],
          start_time: startTime,
          end_time: endTime,
        }),
        api.api.getTracesTimeseriesApiV1TracesOverviewTimeseriesPost({
          task_id: taskId,
          start_time: startTime,
          end_time: endTime,
          bucket_size: bucketSize,
        }),
      ]);

      const overview = overviewResponse.data.overviews.find((o) => o.task_id === taskId);
      const timeSeriesData: TimeSeriesDataPoint[] = timeseriesResponse.data.points.map((point) => ({
        timestamp: point.timestamp,
        tracesCount: point.trace_count,
        tokens: point.trace_token_count,
        cost: point.trace_token_cost,
        successRate: point.continuous_eval_success_rate * 100,
      }));

      return {
        tracesCount: overview?.trace_count ?? 0,
        totalTokens: overview?.trace_token_count ?? 0,
        totalCost: overview?.trace_token_cost ?? 0,
        evalsCount: overview?.eval_count ?? 0,
        successRate: (overview?.continuous_eval_success_rate ?? 1) * 100,
        timeSeriesData,
        xLabelFormat: timeWindow.xLabelFormat,
        tickStep: timeWindow.tickStep,
      };
    },
    staleTime: 30000,
    gcTime: 60000,
    placeholderData: keepPreviousData,
  });
};
