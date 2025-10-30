import {
  infiniteQueryOptions,
  keepPreviousData,
  queryOptions,
} from "@tanstack/react-query";

import { IncomingFilter } from "@/components/traces/components/filtering/mapper";
import { Api } from "@/lib/api";
import { FETCH_SIZE } from "@/lib/constants";
import { getFilteredSessions } from "@/services/tracing";
import { queryKeys } from "@/lib/queryKeys";

export const getSessionsQueryOptions = ({
  api,
  taskId,
  filters,
}: {
  api: Api<unknown>;
  taskId: string;
  filters: IncomingFilter[];
}) =>
  queryOptions({
    queryKey: queryKeys.sessions.list(filters),
    queryFn: () => {
      return getFilteredSessions(api!, {
        taskId: taskId ?? "",
        page: 0,
        pageSize: FETCH_SIZE,
        filters,
      });
    },
  });

export const getSessionsInfiniteQueryOptions = ({
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
    queryKey: [...queryKeys.sessions.list(filters), "infinite"] as const,
    queryFn: ({ pageParam = 0 }) => {
      return getFilteredSessions(api!, {
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
