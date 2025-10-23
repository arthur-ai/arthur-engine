import {
  infiniteQueryOptions,
  keepPreviousData,
  queryOptions,
} from "@tanstack/react-query";

import { IncomingFilter } from "@/components/traces/components/filtering/mapper";
import { Api } from "@/lib/api";
import { FETCH_SIZE } from "@/lib/constants";
import { getFilteredSpans } from "@/services/tracing";

export const getSpansQueryOptions = ({
  api,
  taskId,
  filters,
}: {
  api: Api<unknown>;
  taskId: string;
  filters: IncomingFilter[];
}) =>
  queryOptions({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: ["spans", taskId, filters] as const,
    queryFn: () => {
      return getFilteredSpans(api!, {
        taskId: taskId ?? "",
        page: 0,
        pageSize: FETCH_SIZE,
        filters,
      });
    },
  });

export const getSpansInfiniteQueryOptions = ({
  api,
  taskId,
  filters,
}: {
  api: Api<unknown>;
  taskId: string;
  filters: IncomingFilter[];
}) =>
  infiniteQueryOptions({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: ["spans", taskId, filters, "infinite"] as const,
    queryFn: ({ pageParam = 0 }) => {
      return getFilteredSpans(api!, {
        taskId: taskId ?? "",
        page: pageParam as number,
        pageSize: FETCH_SIZE,
        filters,
      });
    },
    initialPageParam: 0,
    getNextPageParam: (_, __, lastPageParam = 0) => {
      return lastPageParam + 1;
    },
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });
