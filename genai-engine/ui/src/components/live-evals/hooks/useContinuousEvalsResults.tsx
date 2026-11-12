import { IncomingFilter, Operators } from "@arthur/shared-components/traces";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { Api } from "@/lib/api";
import { ContinuousEvalRunLevel, ContinuousEvalRunStatus } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { PaginationParams } from "@/types/common";

// One row per trace verdict: trace-scope runs and span-scope rollups. Span runs
// (one per judged span) are listed when asked for.
export const TRACE_VERDICT_RUN_LEVELS: ContinuousEvalRunLevel[] = ["trace", "span_rollup"];

export const runLevelsFor = (showSpanRuns: boolean): ContinuousEvalRunLevel[] | undefined => (showSpanRuns ? undefined : TRACE_VERDICT_RUN_LEVELS);

export const useContinuousEvalsResults = ({
  pagination,
  filters = [],
  showSpanRuns = false,
}: {
  pagination: PaginationParams;
  filters?: IncomingFilter[];
  showSpanRuns?: boolean;
}) => {
  const { task } = useTask();
  const api = useApi()!;

  return useQuery(continuousEvalsResultsQueryOptions({ api, taskId: task!.id, pagination, filters, showSpanRuns }));
};

export const continuousEvalsResultsQueryOptions = ({
  taskId,
  api,
  pagination,
  filters = [],
  showSpanRuns = false,
}: {
  api: Api<unknown>;
  taskId: string;
  pagination: PaginationParams;
  filters?: IncomingFilter[];
  showSpanRuns?: boolean;
}) =>
  queryOptions({
    queryKey: [queryKeys.continuousEvals.results(taskId), pagination, filters, showSpanRuns],
    queryFn: () =>
      api.api.listContinuousEvalRunResultsApiV1TasksTaskIdContinuousEvalsResultsGet({
        taskId,
        ...pagination,
        ...mapFiltersToRequest(filters),
        run_levels: runLevelsFor(showSpanRuns),
      }),
    select: (data) => data.data,
  });

export const mapFiltersToRequest = (filters: IncomingFilter[]) => {
  const request: Record<string, string | string[] | number> = {};

  filters.forEach((filter) => {
    const key = filter.name;

    if (key === "id") {
      // Convert to array and use plural key
      const value = Array.isArray(filter.value) ? filter.value : [filter.value];
      return (request["ids"] = value as string[]);
    }

    if (key === "continuous_eval_id") {
      // Convert to array and use plural key
      const value = Array.isArray(filter.value) ? filter.value : [filter.value];
      return (request["continuous_eval_ids"] = value as string[]);
    }

    if (key === "trace_id") {
      // Convert to array and use plural key
      const value = Array.isArray(filter.value) ? filter.value : [filter.value];
      return (request["trace_ids"] = value as string[]);
    }

    if (key === "annotation_score") {
      return (request[key] = Number(filter.value));
    }

    if (key === "run_status") {
      return (request[key] = filter.value as ContinuousEvalRunStatus);
    }

    if (key === "eval_name") {
      return (request[key] = filter.value as string);
    }

    if (key === "created_at") {
      if (filter.operator === Operators.GREATER_THAN) {
        return (request["created_after"] = filter.value as string);
      }
      if (filter.operator === Operators.LESS_THAN) {
        return (request["created_before"] = filter.value as string);
      }
    }
  });

  return request;
};
