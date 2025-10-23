import {
  infiniteQueryOptions,
  keepPreviousData,
  queryOptions,
} from "@tanstack/react-query";

import { Api } from "@/lib/api";
import { FETCH_SIZE, MAX_PAGE_SIZE } from "@/lib/constants";
import { getUsers } from "@/services/tracing";

export const getUsersQueryOptions = ({
  api,
  taskId,
}: {
  api: Api<unknown>;
  taskId: string;
}) =>
  queryOptions({
    queryKey: ["users", taskId] as const, // eslint-disable-line @tanstack/query/exhaustive-deps
    queryFn: () =>
      getUsers(api, { taskId, page: 0, pageSize: MAX_PAGE_SIZE, filters: [] }),
  });

export const getUsersInfiniteQueryOptions = ({
  api,
  taskId,
}: {
  api: Api<unknown>;
  taskId: string;
}) =>
  infiniteQueryOptions({
    queryKey: ["users", taskId, "infinite"] as const, // eslint-disable-line @tanstack/query/exhaustive-deps
    queryFn: ({ pageParam = 0 }) =>
      getUsers(api, {
        taskId,
        page: pageParam,
        pageSize: FETCH_SIZE,
        filters: [],
      }),
    initialPageParam: 0,
    getNextPageParam: (_, __, lastPageParam = 0) => {
      return lastPageParam + 1;
    },
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });
