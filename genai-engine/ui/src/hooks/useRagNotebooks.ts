import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { useApi } from "./useApi";
import { useApiMutation } from "./useApiMutation";
import { useApiQuery } from "./useApiQuery";

import { deserializeRagNotebookState } from "@/components/retrievals/utils/ragNotebookStateUtils";
import type {
  RagNotebookDetail,
  CreateRagNotebookRequest,
  UpdateRagNotebookRequest,
  SetRagNotebookStateRequest,
  RagNotebookStateResponse,
  RagExperimentSummary,
} from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

interface RagNotebooksFilters {
  page: number;
  pageSize: number;
  sort: "asc" | "desc";
}

/**
 * Hook to fetch all RAG notebooks for a task
 */
export function useRagNotebooks(taskId: string | undefined, filters: RagNotebooksFilters) {
  const { data, error, isLoading, refetch } = useApiQuery<"listRagNotebooksApiV1TasksTaskIdRagNotebooksGet">({
    method: "listRagNotebooksApiV1TasksTaskIdRagNotebooksGet",
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
 * Hook to fetch a single RAG notebook by ID
 */
export function useRagNotebook(notebookId: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getRagNotebookApiV1RagNotebooksNotebookIdGet">({
    method: "getRagNotebookApiV1RagNotebooksNotebookIdGet",
    args: [notebookId!] as const,
    enabled: !!notebookId,
    queryOptions: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
    },
  });

  return {
    notebook: data as RagNotebookDetail | undefined,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to fetch RAG notebook state and deserialize it to panels
 * This combines fetching the raw state and deserializing it in one query
 */
export function useRagNotebookState(notebookId: string | undefined) {
  const api = useApi();

  const { data, error, isLoading, isSuccess, refetch } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps -- api reference is stable
    queryKey: [...queryKeys.ragNotebooks.state(notebookId!), "deserialized"],
    queryFn: async () => {
      if (!api || !notebookId) throw new Error("API client or notebookId not available");

      const response = await api.api.getRagNotebookStateApiV1RagNotebooksNotebookIdStateGet(notebookId);
      const rawState = response.data as RagNotebookStateResponse;

      // Deserialize the state to panels and experiment config
      const { panels, experimentConfig, fullState } = await deserializeRagNotebookState(rawState, api);

      return { panels, experimentConfig, fullState };
    },
    enabled: !!api && !!notebookId,
    staleTime: 5000,
  });

  return {
    panels: data?.panels,
    experimentConfig: data?.experimentConfig,
    fullState: data?.fullState,
    error,
    isLoading,
    isSuccess,
    refetch,
  };
}

/**
 * Hook to fetch RAG notebook experiment history with polling
 */
export function useRagNotebookHistoryWithPolling(
  notebookId: string | undefined,
  page: number = 0,
  pageSize: number = 25,
  pollInterval: number = 5000
) {
  const { data, error, isLoading, refetch } = useApiQuery<"getRagNotebookHistoryApiV1RagNotebooksNotebookIdHistoryGet">({
    method: "getRagNotebookHistoryApiV1RagNotebooksNotebookIdHistoryGet",
    args: [{ notebookId: notebookId!, page, page_size: pageSize }] as const,
    enabled: !!notebookId,
    queryOptions: {
      staleTime: 2000,
      refetchOnWindowFocus: true,
      refetchInterval: pollInterval,
    },
  });

  // Check if any experiments are still running
  const hasRunningExperiments = useMemo(() => {
    return data?.data?.some((exp: RagExperimentSummary) => exp.status === "queued" || exp.status === "running") ?? false;
  }, [data]);

  return {
    experiments: data?.data ?? [],
    page: data?.page ?? 0,
    pageSize: data?.page_size ?? pageSize,
    totalPages: data?.total_pages ?? 0,
    totalCount: data?.total_count ?? 0,
    hasRunningExperiments,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to create a new RAG notebook
 */
export function useCreateRagNotebookMutation(taskId: string | undefined, onSuccess?: (notebook: RagNotebookDetail) => void) {
  const api = useApi();

  return useApiMutation<RagNotebookDetail, CreateRagNotebookRequest>({
    mutationFn: async (request: CreateRagNotebookRequest) => {
      if (!api || !taskId) throw new Error("API client or taskId not available");

      const response = await api.api.createRagNotebookApiV1TasksTaskIdRagNotebooksPost(taskId, request);
      return response.data;
    },
    onSuccess,
    invalidateQueries: [{ queryKey: queryKeys.ragNotebooks.listAll() }],
  });
}

/**
 * Hook to update RAG notebook metadata
 */
export function useUpdateRagNotebookMutation(onSuccess?: () => void) {
  const api = useApi();

  return useApiMutation<RagNotebookDetail, { notebookId: string; request: UpdateRagNotebookRequest }>({
    mutationFn: async ({ notebookId, request }) => {
      if (!api) throw new Error("API client not available");

      const response = await api.api.updateRagNotebookApiV1RagNotebooksNotebookIdPut(notebookId, request);
      return response.data;
    },
    onSuccess,
    invalidateQueries: [{ queryKey: queryKeys.ragNotebooks.listAll() }, { queryKey: queryKeys.ragNotebooks.detailAll() }],
  });
}

/**
 * Hook to set RAG notebook state
 */
export function useSetRagNotebookStateMutation(onSuccess?: () => void) {
  const api = useApi();

  return useApiMutation<RagNotebookDetail, { notebookId: string; request: SetRagNotebookStateRequest }>({
    mutationFn: async ({ notebookId, request }) => {
      if (!api) throw new Error("API client not available");

      const response = await api.api.setRagNotebookStateApiV1RagNotebooksNotebookIdStatePut(notebookId, request);
      return response.data;
    },
    onSuccess,
    invalidateQueries: [{ queryKey: queryKeys.ragNotebooks.detailAll() }, { queryKey: queryKeys.ragNotebooks.stateAll() }],
  });
}

/**
 * Hook to delete a RAG notebook
 */
export function useDeleteRagNotebookMutation(taskId: string | undefined, onSuccess?: () => void) {
  const api = useApi();

  return useApiMutation<void, string>({
    mutationFn: async (notebookId: string) => {
      if (!api) throw new Error("API client not available");

      await api.api.deleteRagNotebookApiV1RagNotebooksNotebookIdDelete(notebookId);
    },
    onSuccess,
    invalidateQueries: [{ queryKey: queryKeys.ragNotebooks.listAll() }, { queryKey: queryKeys.ragNotebooks.detailAll() }],
  });
}

/**
 * Hook to attach a notebook to a RAG experiment
 */
export function useAttachNotebookToRagExperimentMutation(onSuccess?: () => void) {
  const api = useApi();

  return useApiMutation<RagExperimentSummary, { experimentId: string; notebookId: string }>({
    mutationFn: async ({ experimentId, notebookId }) => {
      if (!api) throw new Error("API client not available");

      const response = await api.api.attachNotebookToRagExperimentApiV1RagExperimentsExperimentIdNotebookPatch({
        experimentId,
        notebook_id: notebookId,
      });
      return response.data;
    },
    onSuccess,
    invalidateQueries: [{ queryKey: queryKeys.ragExperiments.detailAll() }, { queryKey: queryKeys.ragNotebooks.historyAll() }],
  });
}
