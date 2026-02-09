import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApi } from "./useApi";

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
  xLabelFormat: "time" | "date" | "month";
  tickStep: number;
}

interface UseTaskOverviewMetricsParams {
  taskId: string;
  interval: TimeInterval;
}

export const useTaskOverviewMetrics = ({ taskId, interval }: UseTaskOverviewMetricsParams) => {
  const api = useApi()!;

  return useQuery({
    queryKey: queryKeys.metrics.overview(taskId, interval),
    queryFn: async (): Promise<TaskOverviewMetrics> => {
      // Get canonical time window and bucketing parameters
      const queryTime = new Date();
      const timeWindow = getTimeWindowAndBucketing(interval, queryTime);

      const { start: startTime, end: endTime, bucketMs: bucketSize } = timeWindow;

      // Calculate time boundaries in milliseconds
      const startTimeMs = startTime.getTime();
      const endTimeMs = endTime.getTime();

      // Calculate exact number of buckets needed to cover the entire time range
      const durationMs = endTimeMs - startTimeMs;
      const numBuckets = Math.max(1, Math.ceil(durationMs / bucketSize));

      // Fetch all traces for the task within the time range
      const pageSize = 1000;
      let allTraces: any[] = [];
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

        allTraces = [...allTraces, ...response.data.traces];

        // Check if there are more pages
        if (response.data.traces.length < pageSize) {
          hasMore = false;
        } else {
          currentPage++;
        }

        // Safety check: don't fetch more than 10000 traces
        if (allTraces.length >= 10000) {
          hasMore = false;
        }
      }

      // Calculate aggregated metrics - only for traces within our time window
      let totalTokens = 0;
      let totalCost = 0;
      let evalsCount = 0;
      let totalEvalResults = 0;
      let passedEvalResults = 0;
      let tracesInWindow = 0;

      allTraces.forEach((trace) => {
        const traceTime = new Date(trace.created_at).getTime();

        // Skip traces outside our time window
        if (traceTime < startTimeMs || traceTime > endTimeMs) {
          return;
        }

        tracesInWindow++;

        // Sum up tokens
        const promptTokens = trace.prompt_token_count || 0;
        const completionTokens = trace.completion_token_count || 0;
        totalTokens += promptTokens + completionTokens;

        // Sum up costs
        const promptCost = trace.prompt_token_cost || 0;
        const completionCost = trace.completion_token_cost || 0;
        totalCost += promptCost + completionCost;

        // Count eval results from spans if available
        if (trace.spans && Array.isArray(trace.spans)) {
          trace.spans.forEach((span: any) => {
            if (span.metric_results && Array.isArray(span.metric_results)) {
              evalsCount += span.metric_results.length;

              span.metric_results.forEach((result: any) => {
                totalEvalResults++;
                if (result.passed !== false) {
                  passedEvalResults++;
                }
              });
            }
          });
        }
      });

      // Initialize buckets using index as key for reliability
      const buckets = new Map<number, { traces: any[]; timestamp: number }>();
      for (let i = 0; i < numBuckets; i++) {
        // For the last bucket, use the actual end time (now) instead of calculated bucket start
        // This ensures the X-axis shows today's date for the current period
        const bucketTime = i === numBuckets - 1 ? endTimeMs : startTimeMs + i * bucketSize;
        buckets.set(i, { traces: [], timestamp: bucketTime });
      }

      // Assign traces to buckets - only include traces within our time window
      allTraces.forEach((trace) => {
        const traceTime = new Date(trace.created_at).getTime();

        // Skip traces outside our time window
        if (traceTime < startTimeMs || traceTime > endTimeMs) {
          return;
        }

        // Calculate which bucket this trace belongs to
        let bucketIndex = Math.floor((traceTime - startTimeMs) / bucketSize);

        // Clamp to valid range (should rarely be needed now)
        if (bucketIndex < 0) bucketIndex = 0;
        if (bucketIndex >= numBuckets) bucketIndex = numBuckets - 1;

        const bucket = buckets.get(bucketIndex);
        if (bucket) {
          bucket.traces.push(trace);
        }
      });

      // Calculate metrics for each bucket
      const timeSeriesData: TimeSeriesDataPoint[] = Array.from(buckets.entries())
        .sort((a, b) => a[0] - b[0]) // Sort by index
        .map(([index, bucket]) => {
          let bucketTokens = 0;
          let bucketCost = 0;
          let bucketEvalResults = 0;
          let bucketPassedEvals = 0;

          bucket.traces.forEach((trace) => {
            bucketTokens += (trace.prompt_token_count || 0) + (trace.completion_token_count || 0);
            bucketCost += (trace.prompt_token_cost || 0) + (trace.completion_token_cost || 0);

            if (trace.spans && Array.isArray(trace.spans)) {
              trace.spans.forEach((span: any) => {
                if (span.metric_results && Array.isArray(span.metric_results)) {
                  span.metric_results.forEach((result: any) => {
                    bucketEvalResults++;
                    if (result.passed !== false) {
                      bucketPassedEvals++;
                    }
                  });
                }
              });
            }
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
        tracesCount: tracesInWindow,
        totalTokens,
        totalCost,
        evalsCount,
        successRate,
        timeSeriesData,
        xLabelFormat: timeWindow.xLabelFormat,
        tickStep: timeWindow.tickStep,
      };
    },
    staleTime: interval === "hour" ? 10000 : 30000, // 10 seconds for hour view, 30 seconds for others
    gcTime: 60000, // 1 minute
    placeholderData: keepPreviousData,
  });
};
