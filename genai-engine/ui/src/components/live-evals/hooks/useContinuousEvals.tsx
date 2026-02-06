import { queryOptions, useQuery } from "@tanstack/react-query";

import { IncomingFilter } from "@/components/traces/components/filtering/mapper";
import { Operators } from "@/components/traces/components/filtering/types";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { PaginationParams } from "@/types/common";

export const useContinuousEvals = ({ pagination, filters = [] }: { pagination: PaginationParams; filters?: IncomingFilter[] }) => {
  const { task } = useTask();
  const api = useApi()!;

  return useQuery(continuousEvalsQueryOptions({ api, taskId: task!.id, pagination, filters }));
};

export const continuousEvalsQueryOptions = ({
  api,
  taskId,
  pagination,
  filters = [],
}: {
  api: Api<unknown>;
  taskId: string;
  pagination: PaginationParams;
  filters?: IncomingFilter[];
}) =>
  queryOptions({
    queryKey: [queryKeys.continuousEvals.all(taskId), pagination, filters],
    queryFn: () => api.api.listContinuousEvalsApiV1TasksTaskIdContinuousEvalsGet({ taskId, ...pagination, ...mapFiltersToRequest(filters) }),
    select: (data) => data.data,
  });

const mapFiltersToRequest = (filters: IncomingFilter[]) => {
  const request: Record<string, string | number | string[]> = {};

  filters.forEach((filter) => {
    const key = filter.name;

    if (key === "name") {
      return (request[key] = filter.value as string);
    }

    if (key === "llm_eval_name") {
      return (request[key] = filter.value as string);
    }

    if (key === "enabled") {
      return (request[key] = filter.value as string);
    }

    if (key === "continuous_eval_id") {
      return (request["continuous_eval_ids"] = filter.value as string[]);
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
