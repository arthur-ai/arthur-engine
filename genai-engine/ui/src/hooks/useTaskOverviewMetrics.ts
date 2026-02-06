import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApi } from "./useApi";

import { getStartDate } from "@/components/traces/components/filtering/mapper";
import { TimeRange } from "@/components/traces/constants";
import { queryKeys } from "@/lib/queryKeys";

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
}

interface UseTaskOverviewMetricsParams {
  taskId: string;
  timeRange: TimeRange;
}

// Helper to get bucket size in milliseconds based on time range
const getBucketSize = (timeRange: TimeRange): number => {
  const ranges: Record<string, number> = {
    "5 minutes": 30 * 1000, // 30 second buckets
    "30 minutes": 2 * 60 * 1000, // 2 minute buckets
    "1 day": 2 * 60 * 60 * 1000, // 2 hour buckets (12 buckets per day)
    "1 week": 24 * 60 * 60 * 1000, // 1 day buckets (7 buckets per week)
    "1 month": 24 * 60 * 60 * 1000, // 1 day buckets (~30 buckets per month)
    "3 months": 7 * 24 * 60 * 60 * 1000, // 1 week buckets (~13 buckets)
    "1 year": 30 * 24 * 60 * 60 * 1000, // 1 month buckets (12 buckets per year)
    "all time": 30 * 24 * 60 * 60 * 1000, // 1 month buckets
  };
  return ranges[timeRange] || 24 * 60 * 60 * 1000; // default to 1 day
};

export const useTaskOverviewMetrics = ({ taskId, timeRange }: UseTaskOverviewMetricsParams) => {
  const api = useApi()!;

  return useQuery({
    queryKey: queryKeys.metrics.overview(taskId, timeRange),
    queryFn: async (): Promise<TaskOverviewMetrics> => {
      const startTime = getStartDate(timeRange);

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

      // Calculate aggregated metrics
      let totalTokens = 0;
      let totalCost = 0;
      let evalsCount = 0;
      let totalEvalResults = 0;
      let passedEvalResults = 0;

      allTraces.forEach((trace) => {
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

      // Calculate time series data
      const bucketSize = getBucketSize(timeRange);
      const now = Date.now();
      const startTimeMs = startTime.getTime();

      // Create buckets - ensure at least 7 buckets for better visualization
      const calculatedBuckets = Math.ceil((now - startTimeMs) / bucketSize);
      const numBuckets = Math.max(calculatedBuckets, 7);

      // Initialize buckets using index as key for reliability
      const buckets = new Map<number, { traces: any[]; timestamp: number }>();
      for (let i = 0; i < numBuckets; i++) {
        const bucketTime = startTimeMs + i * bucketSize;
        buckets.set(i, { traces: [], timestamp: bucketTime });
      }

      // Assign traces to buckets
      allTraces.forEach((trace) => {
        const traceTime = new Date(trace.created_at).getTime();

        // Calculate which bucket this trace belongs to
        let bucketIndex = Math.floor((traceTime - startTimeMs) / bucketSize);

        // Clamp to valid range
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
        tracesCount: allTraces.length,
        totalTokens,
        totalCost,
        evalsCount,
        successRate,
        timeSeriesData,
      };
    },
    staleTime: 30000, // 30 seconds
    gcTime: 60000, // 1 minute
    placeholderData: keepPreviousData,
  });
};
