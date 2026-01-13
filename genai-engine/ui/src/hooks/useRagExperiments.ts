import { useApi } from "./useApi";
import { useApiMutation } from "./useApiMutation";
import { useApiQuery } from "./useApiQuery";

import type { CreateRagExperimentRequest, RagExperimentDetail, RagExperimentListResponse, RagExperimentSummary } from "@/lib/api-client/api-client";
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
  datasetId?: string,
  pollInterval: number = 3000
) {
  const { data, error, isLoading, refetch } = useApiQuery<"listRagExperimentsApiV1TasksTaskIdRagExperimentsGet">({
    method: "listRagExperimentsApiV1TasksTaskIdRagExperimentsGet",
    args: [{ taskId: taskId!, page, page_size: pageSize, search, dataset_id: datasetId }] as const,
    enabled: !!taskId,
    queryOptions: {
      staleTime: 1000,
      refetchOnWindowFocus: true,
      // Poll when any experiment is running or queued
      refetchInterval: (query) => {
        const response = query.state.data as RagExperimentListResponse | undefined;
        if (!response?.data) return false;
        const hasRunningExperiments = response.data.some((exp) => exp.status === "running" || exp.status === "queued");
        return hasRunningExperiments ? pollInterval : false;
      },
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
 * Automatically polls every 3 seconds while the experiment is running
 */
export function useRagExperimentWithPolling(experimentId: string | undefined, enabled: boolean = true, pollInterval: number = 3000) {
  const { data, error, isLoading, refetch } = useApiQuery<"getRagExperimentApiV1RagExperimentsExperimentIdGet">({
    method: "getRagExperimentApiV1RagExperimentsExperimentIdGet",
    args: [experimentId!] as const,
    enabled: !!experimentId && enabled,
    queryOptions: {
      staleTime: 1000,
      refetchOnWindowFocus: true,
      // Only poll if experiment is in a running state
      refetchInterval: (query) => {
        const experiment = query.state.data as RagExperimentDetail | undefined;
        if (!experiment) return false;
        const isRunning = experiment.status === "running" || experiment.status === "queued";
        return isRunning ? pollInterval : false;
      },
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
