import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApi } from "./useApi";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { TraceMetadataResponse } from "@/lib/api-client/api-client";
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

function getTraceTokens(trace: TraceMetadataResponse): number {
  return trace.total_token_count ?? (trace.prompt_token_count || 0) + (trace.completion_token_count || 0);
}

function getTraceCost(trace: TraceMetadataResponse): number {
  return trace.total_token_cost ?? (trace.prompt_token_cost || 0) + (trace.completion_token_cost || 0);
}

function getTraceEvalStats(trace: TraceMetadataResponse): { total: number; passed: number } {
  let total = 0;
  let passed = 0;

  // Count from annotations (continuous_eval type with a definitive run_status)
  if (trace.annotations && Array.isArray(trace.annotations)) {
    trace.annotations.forEach((annotation) => {
      if (annotation.annotation_type === "continuous_eval" && annotation.run_status) {
        total++;
        if (annotation.run_status === "passed") {
          passed++;
        }
      }
    });
  }

  return { total, passed };
}

export const useTaskOverviewMetrics = ({ taskId, interval }: UseTaskOverviewMetricsParams) => {
  const api = useApi()!;
  const { timezone } = useDisplaySettings();

  return useQuery({
    queryKey: queryKeys.metrics.overview(taskId, interval),
    enabled: !!taskId,
    queryFn: async (): Promise<TaskOverviewMetrics> => {
      const queryTime = new Date();
      const timeWindow = getTimeWindowAndBucketing(interval, queryTime, { timezone });

      const { start: startTime, end: endTime, bucketMs: bucketSize } = timeWindow;

      const startTimeMs = startTime.getTime();
      const endTimeMs = endTime.getTime();

      const durationMs = endTimeMs - startTimeMs;
      const numBuckets = Math.max(1, Math.ceil(durationMs / bucketSize));

      // Fetch all traces for the task within the time range
      const pageSize = 1000;
      let allTraces: TraceMetadataResponse[] = [];
      let currentPage = 0;
      let hasMore = true;

      while (hasMore) {
        const response = await api.api.listTracesMetadataApiV1TracesGet({
          task_ids: [taskId],
          page: currentPage,
          page_size: pageSize,
          start_time: startTime.toISOString(),
          sort: "desc",
        });

        const traces = response.data.traces;
        allTraces = [...allTraces, ...traces];

        if (traces.length < pageSize) {
          hasMore = false;
        } else {
          currentPage++;
        }

        if (allTraces.length >= 10000) {
          hasMore = false;
        }
      }

      // Aggregate metrics
      let totalTokens = 0;
      let totalCost = 0;
      let totalEvalResults = 0;
      let passedEvalResults = 0;

      allTraces.forEach((trace) => {
        totalTokens += getTraceTokens(trace);
        totalCost += getTraceCost(trace);

        const evalStats = getTraceEvalStats(trace);
        totalEvalResults += evalStats.total;
        passedEvalResults += evalStats.passed;
      });

      // Initialize time buckets
      const buckets = new Map<number, { traces: TraceMetadataResponse[]; timestamp: number }>();
      for (let i = 0; i < numBuckets; i++) {
        const bucketTime = i === numBuckets - 1 ? endTimeMs : startTimeMs + i * bucketSize;
        buckets.set(i, { traces: [], timestamp: bucketTime });
      }

      // Assign traces to buckets
      allTraces.forEach((trace) => {
        const traceTime = new Date(trace.created_at).getTime();

        let bucketIndex = Math.floor((traceTime - startTimeMs) / bucketSize);
        if (bucketIndex < 0) bucketIndex = 0;
        if (bucketIndex >= numBuckets) bucketIndex = numBuckets - 1;

        const bucket = buckets.get(bucketIndex);
        if (bucket) {
          bucket.traces.push(trace);
        }
      });

      // Calculate metrics per bucket
      const timeSeriesData: TimeSeriesDataPoint[] = Array.from(buckets.entries())
        .sort((a, b) => a[0] - b[0])
        .map(([_index, bucket]) => {
          let bucketTokens = 0;
          let bucketCost = 0;
          let bucketEvalResults = 0;
          let bucketPassedEvals = 0;

          bucket.traces.forEach((trace) => {
            bucketTokens += getTraceTokens(trace);
            bucketCost += getTraceCost(trace);

            const evalStats = getTraceEvalStats(trace);
            bucketEvalResults += evalStats.total;
            bucketPassedEvals += evalStats.passed;
          });

          const successRate = bucketEvalResults > 0 ? (bucketPassedEvals / bucketEvalResults) * 100 : 100;

          return {
            timestamp: new Date(bucket.timestamp).toISOString(),
            tracesCount: bucket.traces.length,
            tokens: bucketTokens,
            cost: bucketCost,
            successRate,
          };
        });

      const successRate = totalEvalResults > 0 ? (passedEvalResults / totalEvalResults) * 100 : 100;

      return {
        tracesCount: allTraces.length,
        totalTokens,
        totalCost,
        evalsCount: totalEvalResults,
        successRate,
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
