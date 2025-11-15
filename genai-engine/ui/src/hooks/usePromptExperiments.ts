import { useApiQuery } from "./useApiQuery";
import { useApiMutation } from "./useApiMutation";
import { useApi } from "./useApi";

import type {
  PromptExperimentListResponse,
  PromptExperimentDetail,
  TestCaseListResponse,
  CreatePromptExperimentRequest,
  PromptExperimentSummary,
} from "@/lib/api-client/api-client";

/**
 * Hook to fetch all prompt experiments for a task
 */
export function usePromptExperiments(
  taskId: string | undefined,
  page: number = 0,
  pageSize: number = 100
) {
  const { data, error, isLoading, refetch } = useApiQuery<"listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet">({
    method: "listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet",
    args: [{ taskId: taskId!, page, page_size: pageSize }] as const,
    enabled: !!taskId,
    queryOptions: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
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
 * Hook to fetch a single prompt experiment by ID
 */
export function usePromptExperiment(experimentId: string | undefined) {
  const { data, error, isLoading, refetch } = useApiQuery<"getPromptExperimentApiV1PromptExperimentsExperimentIdGet">({
    method: "getPromptExperimentApiV1PromptExperimentsExperimentIdGet",
    args: [experimentId!] as const,
    enabled: !!experimentId,
    queryOptions: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
    },
  });

  return {
    experiment: data as PromptExperimentDetail | undefined,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to fetch test cases for an experiment
 */
export function useExperimentTestCases(
  experimentId: string | undefined,
  page: number = 1,
  pageSize: number = 20
) {
  const { data, error, isLoading, refetch } = useApiQuery<"getExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGet">({
    method: "getExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGet",
    args: [{ experimentId: experimentId!, page, page_size: pageSize }] as const,
    enabled: !!experimentId,
    queryOptions: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
    },
  });

  return {
    testCases: data?.data ?? [],
    page: data?.page ?? 1,
    pageSize: data?.page_size ?? pageSize,
    totalPages: data?.total_pages ?? 0,
    totalCount: data?.total_count ?? 0,
    error,
    isLoading,
    refetch,
  };
}

/**
 * Hook to create a new prompt experiment
 */
export function useCreateExperiment(taskId: string | undefined) {
  const api = useApi();

  return useApiMutation<PromptExperimentSummary, CreatePromptExperimentRequest>({
    mutationFn: async (request: CreatePromptExperimentRequest) => {
      if (!api || !taskId) throw new Error("API client or taskId not available");

      const response = await api.api.createPromptExperimentApiV1TasksTaskIdPromptExperimentsPost(
        taskId,
        request
      );
      return response.data;
    },
    invalidateQueries: [
      { queryKey: ["listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet"] },
    ],
  });
}
