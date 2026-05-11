import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { useApi } from "./useApi";

import type { SearchTasksResponse, TaskResponse } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

const ACTIVE_PAGE_SIZE = 50;
const ARCHIVED_PAGE_SIZE = 500;

export function useActiveTasksQuery({ search }: { search: string }) {
  const { api } = useApi()!;
  const trimmedSearch = search.trim();

  const query = useInfiniteQuery<SearchTasksResponse, Error>({
    queryKey: [...queryKeys.tasks.list(), { search: trimmedSearch }],
    queryFn: async ({ pageParam }) => {
      const response = await api.searchTasksApiV2TasksSearchPost(
        { page_size: ACTIVE_PAGE_SIZE, page: pageParam as number },
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

export function useArchivedTasksQuery({ enabled }: { enabled: boolean }) {
  const { api } = useApi()!;

  const query = useInfiniteQuery<SearchTasksResponse, Error>({
    queryKey: queryKeys.tasks.archived(),
    queryFn: async ({ pageParam }) => {
      const response = await api.searchTasksApiV2TasksSearchPost(
        { page_size: ARCHIVED_PAGE_SIZE, page: pageParam as number },
        { only_archived: true }
      );
      return response.data;
    },
    enabled: !!api && enabled,
    initialPageParam: 0,
    getNextPageParam: () => undefined,
  });

  const tasks: TaskResponse[] = useMemo(() => query.data?.pages.flatMap((p) => p.tasks ?? []) ?? [], [query.data]);

  return {
    tasks,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}
