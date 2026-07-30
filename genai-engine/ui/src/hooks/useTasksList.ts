import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { useApi } from "./useApi";

import type { SearchTasksResponse, TaskResponse } from "@/lib/api";
import type { PaginationSortMethod, TaskSortField } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

const ACTIVE_PAGE_SIZE = 50;
const ARCHIVED_PAGE_SIZE = 50;

export interface TaskListQueryOptions {
  sortField?: TaskSortField;
  sort?: PaginationSortMethod;
  // ISO-8601 UTC timestamp; when set, only tasks whose last trace activity is
  // on or after this time are returned (server-side "Active in last N days").
  lastActiveStartTime?: string;
}

export function useActiveTasksQuery({ search, sortField, sort, lastActiveStartTime }: { search: string } & TaskListQueryOptions) {
  const { api } = useApi()!;
  const trimmedSearch = search.trim();

  const query = useInfiniteQuery<SearchTasksResponse, Error>({
    queryKey: [...queryKeys.tasks.list(), { search: trimmedSearch, sortField, sort, lastActiveStartTime }],
    queryFn: async ({ pageParam }) => {
      const response = await api.searchTasksApiV2TasksSearchPost(
        {
          page_size: ACTIVE_PAGE_SIZE,
          page: pageParam as number,
          ...(sortField ? { sort_field: sortField } : {}),
          ...(sort ? { sort } : {}),
          ...(lastActiveStartTime ? { last_active_start_time: lastActiveStartTime } : {}),
        },
        trimmedSearch ? { task_name: trimmedSearch } : {}
      );
      return response.data;
    },
    enabled: !!api,
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if ((lastPage.tasks?.length ?? 0) === 0) return undefined;
      const loaded = allPages.reduce((sum, p) => sum + (p.tasks?.length ?? 0), 0);
      const total = lastPage.count ?? 0;
      return loaded < total ? allPages.length : undefined;
    },
    placeholderData: keepPreviousData,
  });

  const tasks: TaskResponse[] = useMemo(() => query.data?.pages.flatMap((p) => p.tasks ?? []) ?? [], [query.data]);
  const lastPage = query.data?.pages[query.data.pages.length - 1];
  const totalCount = lastPage?.count ?? 0;

  return {
    tasks,
    totalCount,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
  };
}

export function useArchivedTasksQuery({ enabled, sortField, sort }: { enabled: boolean } & TaskListQueryOptions) {
  const { api } = useApi()!;

  const query = useInfiniteQuery<SearchTasksResponse, Error>({
    queryKey: [...queryKeys.tasks.archived(), { sortField, sort }],
    queryFn: async ({ pageParam }) => {
      const response = await api.searchTasksApiV2TasksSearchPost(
        {
          page_size: ARCHIVED_PAGE_SIZE,
          page: pageParam as number,
          ...(sortField ? { sort_field: sortField } : {}),
          ...(sort ? { sort } : {}),
        },
        { only_archived: true }
      );
      return response.data;
    },
    enabled: !!api && enabled,
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if ((lastPage.tasks?.length ?? 0) === 0) return undefined;
      const loaded = allPages.reduce((sum, p) => sum + (p.tasks?.length ?? 0), 0);
      const total = lastPage.count ?? 0;
      return loaded < total ? allPages.length : undefined;
    },
  });

  const tasks: TaskResponse[] = useMemo(() => query.data?.pages.flatMap((p) => p.tasks ?? []) ?? [], [query.data]);
  const lastPage = query.data?.pages[query.data.pages.length - 1];
  const totalCount = lastPage?.count ?? 0;

  return {
    tasks,
    totalCount,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
  };
}
