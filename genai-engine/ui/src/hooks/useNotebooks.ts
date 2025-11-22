import { useApiQuery } from "./useApiQuery";
import { useApiMutation } from "./useApiMutation";
import { useApi } from "./useApi";

import type {
  NotebookListResponse,
  NotebookDetail,
  NotebookSummary,
  CreateNotebookRequest,
  UpdateNotebookRequest,
  SetNotebookStateRequest,
  NotebookState,
  PromptExperimentListResponse,
} from "@/lib/api-client/api-client";

interface NotebooksFilters {
  page: number;
  pageSize: number;
  sort: "asc" | "desc";
}

/**
 * Hook to fetch all notebooks for a task
 */
export function useNotebooks(
  taskId: string | undefined,
  filters: NotebooksFilters
) {
  const { data, error, isLoading, refetch } = useApiQuery<"listNotebooksApiV1TasksTaskIdNotebooksGet">({
    method: "listNotebooksApiV1TasksTaskIdNotebooksGet",
    args: [{ taskId: taskId!, page: filters.page, page_size: filters.pageSize }] as const,
    enabled: !!taskId,
    queryOptions: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
    },
  });

  return {
    notebooks: data?.data ?? [],
    count: data?.total_count ?? 0,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to fetch a single notebook by ID
 */
export function useNotebook(notebookId: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getNotebookApiV1NotebooksNotebookIdGet">({
    method: "getNotebookApiV1NotebooksNotebookIdGet",
    args: [notebookId!] as const,
    enabled: !!notebookId,
    queryOptions: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
    },
  });

  return {
    notebook: data as NotebookDetail | undefined,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to fetch notebook state
 */
export function useNotebookState(notebookId: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getNotebookStateApiV1NotebooksNotebookIdStateGet">({
    method: "getNotebookStateApiV1NotebooksNotebookIdStateGet",
    args: [notebookId!] as const,
    enabled: !!notebookId,
    queryOptions: {
      staleTime: 5000,
    },
  });

  return {
    state: data as NotebookState | undefined,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to fetch notebook experiment history
 */
export function useNotebookHistory(
  notebookId: string | undefined,
  page: number = 0,
  pageSize: number = 25
) {
  const { data, error, isLoading, refetch } = useApiQuery<"getNotebookHistoryApiV1NotebooksNotebookIdHistoryGet">({
    method: "getNotebookHistoryApiV1NotebooksNotebookIdHistoryGet",
    args: [{ notebookId: notebookId!, page, page_size: pageSize }] as const,
    enabled: !!notebookId,
    queryOptions: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
    },
  });

  return {
    experiments: data?.data ?? [],
    page: data?.page ?? 0,
    pageSize: data?.page_size ?? pageSize,
    totalPages: data?.total_pages ?? 0,
    totalCount: data?.total_count ?? 0,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to create a new notebook
 */
export function useCreateNotebookMutation(
  taskId: string | undefined,
  onSuccess?: (notebook: NotebookDetail) => void
) {
  const api = useApi();

  return useApiMutation<NotebookDetail, CreateNotebookRequest>({
    mutationFn: async (request: CreateNotebookRequest) => {
      if (!api || !taskId) throw new Error("API client or taskId not available");

      const response = await api.api.createNotebookApiV1TasksTaskIdNotebooksPost(
        taskId,
        request
      );
      return response.data;
    },
    onSuccess,
    invalidateQueries: [
      { queryKey: ["listNotebooksApiV1TasksTaskIdNotebooksGet"] },
    ],
  });
}

/**
 * Hook to update notebook metadata
 */
export function useUpdateNotebookMutation(
  taskId: string | undefined,
  onSuccess?: () => void
) {
  const api = useApi();

  return useApiMutation<NotebookDetail, { notebookId: string; request: UpdateNotebookRequest }>({
    mutationFn: async ({ notebookId, request }) => {
      if (!api) throw new Error("API client not available");

      const response = await api.api.updateNotebookApiV1NotebooksNotebookIdPut(
        notebookId,
        request
      );
      return response.data;
    },
    onSuccess,
    invalidateQueries: [
      { queryKey: ["listNotebooksApiV1TasksTaskIdNotebooksGet"] },
      { queryKey: ["getNotebookApiV1NotebooksNotebookIdGet"] },
    ],
  });
}

/**
 * Hook to set notebook state
 */
export function useSetNotebookStateMutation(onSuccess?: () => void) {
  const api = useApi();

  return useApiMutation<NotebookDetail, { notebookId: string; request: SetNotebookStateRequest }>({
    mutationFn: async ({ notebookId, request }) => {
      if (!api) throw new Error("API client not available");

      const response = await api.api.setNotebookStateApiV1NotebooksNotebookIdStatePut(
        notebookId,
        request
      );
      return response.data;
    },
    onSuccess,
    invalidateQueries: [
      { queryKey: ["getNotebookApiV1NotebooksNotebookIdGet"] },
      { queryKey: ["getNotebookStateApiV1NotebooksNotebookIdStateGet"] },
    ],
  });
}

/**
 * Hook to delete a notebook
 */
export function useDeleteNotebookMutation(
  taskId: string | undefined,
  onSuccess?: () => void
) {
  const api = useApi();

  return useApiMutation<void, string>({
    mutationFn: async (notebookId: string) => {
      if (!api) throw new Error("API client not available");

      await api.api.deleteNotebookApiV1NotebooksNotebookIdDelete(notebookId);
    },
    onSuccess,
    invalidateQueries: [
      { queryKey: ["listNotebooksApiV1TasksTaskIdNotebooksGet"] },
      { queryKey: ["getNotebookApiV1NotebooksNotebookIdGet"] },
    ],
  });
}

/**
 * Hook to attach an experiment to a notebook
 */
export function useAttachExperimentToNotebookMutation(
  onSuccess?: () => void
) {
  const api = useApi();

  return useApiMutation<NotebookSummary, { experimentId: string; notebookId: string }>({
    mutationFn: async ({ experimentId, notebookId }) => {
      if (!api) throw new Error("API client not available");

      // The generated API client expects experimentId and notebook_id in the params object
      const response = await api.api.attachNotebookToExperimentApiV1PromptExperimentsExperimentIdNotebookPatch(
        { experimentId, notebook_id: notebookId }
      );
      return response.data;
    },
    onSuccess,
    invalidateQueries: [
      { queryKey: ["getPromptExperimentApiV1PromptExperimentsExperimentIdGet"] },
      { queryKey: ["getNotebookHistoryApiV1NotebooksNotebookIdHistoryGet"] },
    ],
  });
}

