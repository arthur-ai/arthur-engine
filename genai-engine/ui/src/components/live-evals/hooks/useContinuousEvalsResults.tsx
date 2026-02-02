import { queryOptions, useQuery } from "@tanstack/react-query";

import { IncomingFilter } from "@/components/traces/components/filtering/mapper";
import { Operators } from "@/components/traces/components/filtering/types";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { Api } from "@/lib/api";
import { ContinuousEvalRunStatus } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { PaginationParams } from "@/types/common";

export const useContinuousEvalsResults = ({ pagination, filters = [] }: { pagination: PaginationParams; filters?: IncomingFilter[] }) => {
  const { task } = useTask();
  const api = useApi()!;

  return useQuery(continuousEvalsResultsQueryOptions({ api, taskId: task!.id, pagination, filters }));
};

export const continuousEvalsResultsQueryOptions = ({
  taskId,
  api,
  pagination,
  filters = [],
}: {
  api: Api<unknown>;
  taskId: string;
  pagination: PaginationParams;
  filters?: IncomingFilter[];
}) =>
  queryOptions({
    queryKey: [queryKeys.continuousEvals.results(taskId), pagination, filters],
    queryFn: () =>
      api.api.listContinuousEvalRunResultsApiV1TasksTaskIdContinuousEvalsResultsGet({ taskId, ...pagination, ...mapFiltersToRequest(filters) }),
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
