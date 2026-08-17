import { IncomingFilter, Operators } from "@arthur/shared-components";
import { keepPreviousData, queryOptions, useInfiniteQuery, useQuery } from "@tanstack/react-query";

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

export const useInfiniteContinuousEvals = ({ pageSize, filters = [] }: { pageSize: number; filters?: IncomingFilter[] }) => {
  const { task } = useTask();
  const api = useApi()!;
  const taskId = task!.id;

  return useInfiniteQuery({
    queryKey: [queryKeys.continuousEvals.all(taskId), "infinite", { pageSize }, filters],
    queryFn: async ({ pageParam }) => {
      const response = await api.api.listContinuousEvalsApiV1TasksTaskIdContinuousEvalsGet({
        taskId,
        page: pageParam,
        page_size: pageSize,
        ...mapFiltersToRequest(filters),
      });
      return response.data;
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if ((lastPage.evals?.length ?? 0) === 0) return undefined;
      const loaded = allPages.reduce((sum, page) => sum + (page.evals?.length ?? 0), 0);
      return loaded < lastPage.count ? allPages.length : undefined;
    },
    placeholderData: keepPreviousData,
  });
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
