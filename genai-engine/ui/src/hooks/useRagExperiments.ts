import { useApi } from "./useApi";
import { useApiMutation } from "./useApiMutation";
import { useApiQuery } from "./useApiQuery";

import type { CreateRagExperimentRequest, RagExperimentDetail, RagExperimentSummary } from "@/lib/api-client/api-client";
import { pollWhileAnyInProgress, pollWhileInProgress, isInProgressStatus, POLL_INTERVAL } from "@/lib/polling";
import { queryKeys } from "@/lib/queryKeys";

/**
 * Hook to fetch all RAG experiments with automatic polling when any experiment is running.
 * Uses TanStack Query's refetchInterval to conditionally poll based on experiment status.
 */
export function useRagExperimentsWithPolling(
  taskId: string | undefined,
  page: number = 0,
  pageSize: number = 100,
  search?: string,
  datasetId?: string
) {
  const { data, error, isLoading, refetch } = useApiQuery<"listRagExperimentsApiV1TasksTaskIdRagExperimentsGet">({
    method: "listRagExperimentsApiV1TasksTaskIdRagExperimentsGet",
    args: [{ taskId: taskId!, page, page_size: pageSize, search, dataset_id: datasetId }] as const,
    enabled: !!taskId,
    queryOptions: {
      staleTime: 1000,
      refetchOnWindowFocus: true,
      refetchInterval: pollWhileAnyInProgress(
        (data) => data?.data,
        (exp) => exp.status,
        POLL_INTERVAL.DEFAULT
      ),
    },
  });

  return {
    experiments: data?.data ?? [],
    page: data?.page,
    pageSize: data?.page_size,
    totalPages: data?.total_pages,
    totalCount: data?.total_count,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to fetch a single RAG experiment with polling for running experiments
 * Automatically polls while the experiment is in progress
 */
export function useRagExperimentWithPolling(experimentId: string | undefined, enabled: boolean = true) {
  const { data, error, isLoading, refetch } = useApiQuery<"getRagExperimentApiV1RagExperimentsExperimentIdGet">({
    method: "getRagExperimentApiV1RagExperimentsExperimentIdGet",
    args: [experimentId!] as const,
    enabled: !!experimentId && enabled,
    queryOptions: {
      staleTime: 1000,
      refetchOnWindowFocus: true,
      refetchInterval: pollWhileInProgress((data) => data?.status, POLL_INTERVAL.DEFAULT),
    },
  });

  return {
    experiment: data as RagExperimentDetail | undefined,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to create a new RAG experiment
 */
export function useCreateRagExperiment(taskId: string | undefined) {
  const api = useApi();

  return useApiMutation<RagExperimentSummary, CreateRagExperimentRequest>({
    mutationFn: async (request: CreateRagExperimentRequest) => {
      if (!api || !taskId) throw new Error("API client or taskId not available");

      const response = await api.api.createRagExperimentApiV1TasksTaskIdRagExperimentsPost(taskId, request);
      return response.data;
    },
    invalidateQueries: [
      { queryKey: queryKeys.ragExperiments.listAll() },
      { queryKey: queryKeys.ragNotebooks.historyAll() },
      { queryKey: queryKeys.ragNotebooks.listAll() },
    ],
  });
}

/**
 * Hook to delete a RAG experiment
 */
export function useDeleteRagExperiment() {
  const api = useApi();

  return useApiMutation<void, string>({
    mutationFn: async (experimentId: string) => {
      if (!api) throw new Error("API client not available");

      await api.api.deleteRagExperimentApiV1RagExperimentsExperimentIdDelete(experimentId);
    },
    invalidateQueries: [
      { queryKey: queryKeys.ragExperiments.listAll() },
      { queryKey: queryKeys.ragExperiments.detailAll() },
      { queryKey: queryKeys.ragNotebooks.historyAll() },
      { queryKey: queryKeys.ragNotebooks.listAll() },
    ],
  });
}

/**
 * Hook to fetch test cases for a RAG experiment with polling support
 * Automatically polls while the experiment is in progress
 */
export function useRagExperimentTestCases(experimentId: string | undefined, page: number = 0, pageSize: number = 20, experimentStatus?: string) {
  const { data, error, isLoading, refetch, isFetching } = useApiQuery<"getRagExperimentTestCasesApiV1RagExperimentsExperimentIdTestCasesGet">({
    method: "getRagExperimentTestCasesApiV1RagExperimentsExperimentIdTestCasesGet",
    args: [{ experimentId: experimentId!, page, page_size: pageSize }] as const,
    enabled: !!experimentId,
    queryOptions: {
      staleTime: 1000,
      refetchOnWindowFocus: true,
      refetchInterval: () => {
        return isInProgressStatus(experimentStatus) ? POLL_INTERVAL.DEFAULT : false;
      },
    },
  });

  return {
    testCases: data?.data ?? [],
    page: data?.page ?? 0,
    pageSize: data?.page_size ?? pageSize,
    totalPages: data?.total_pages ?? 0,
    totalCount: data?.total_count ?? 0,
    error,
    isLoading,
    isFetching,
    refetch,
  };
}
