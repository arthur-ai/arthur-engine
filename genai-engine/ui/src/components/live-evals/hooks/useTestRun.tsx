import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useSnackbar } from "notistack";

import { useApi } from "@/hooks/useApi";
import type { Api } from "@/lib/api";
import type { ContinuousEvalTestRunResponse } from "@/lib/api-client/api-client";
import { pollWhileAnyInProgress, pollWhileInProgress, POLL_INTERVAL } from "@/lib/polling";
import { queryKeys } from "@/lib/queryKeys";

// --- Query options ---

export function testRunQueryOptions({ api, testRunId }: { api: Api<unknown>; testRunId: string }) {
  return {
    queryKey: queryKeys.continuousEvals.testRuns.byId(testRunId),
    queryFn: async () => {
      const res = await api.api.getTestRunApiV1ContinuousEvalsTestRunsTestRunIdGet(testRunId);
      return res.data;
    },
  };
}

export function testRunResultsQueryOptions({
  api,
  testRunId,
  page = 0,
  pageSize = 50,
}: {
  api: Api<unknown>;
  testRunId: string;
  page?: number;
  pageSize?: number;
}) {
  return {
    queryKey: [...queryKeys.continuousEvals.testRuns.results(testRunId), { page, pageSize }],
    queryFn: async () => {
      const res = await api.api.getTestRunResultsApiV1ContinuousEvalsTestRunsTestRunIdResultsGet({
        testRunId,
        page,
        page_size: pageSize,
      });
      return res.data;
    },
  };
}

export function testRunsListQueryOptions({
  api,
  evalId,
  page = 0,
  pageSize = 10,
}: {
  api: Api<unknown>;
  evalId: string;
  page?: number;
  pageSize?: number;
}) {
  return {
    queryKey: [...queryKeys.continuousEvals.testRuns.byEval(evalId), { page, pageSize }],
    queryFn: async () => {
      const res = await api.api.listTestRunsApiV1ContinuousEvalsEvalIdTestRunsGet({
        evalId,
        page,
        page_size: pageSize,
        sort: "desc",
      });
      return res.data;
    },
  };
}

// --- Hooks ---

export function useTestRunsList(evalId: string | undefined, page: number = 0, pageSize: number = 10) {
  const api = useApi()!;

  return useQuery({
    ...testRunsListQueryOptions({ api, evalId: evalId ?? "", page, pageSize }),
    enabled: !!evalId,
    refetchInterval: pollWhileAnyInProgress(
      (data) => data?.test_runs,
      (run) => run.status,
      POLL_INTERVAL.FAST
    ),
  });
}

export function useDeleteTestRun(evalId: string) {
  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (testRunId: string) => {
      await api.api.deleteTestRunApiV1ContinuousEvalsTestRunsTestRunIdDelete(testRunId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.continuousEvals.testRuns.byEval(evalId) });
      enqueueSnackbar("Test run deleted", { variant: "success" });
    },
    onError: (error) => {
      let message = "Failed to delete test run";
      if (isAxiosError(error)) {
        message = error.response?.data.detail ?? message;
      }
      enqueueSnackbar(message, { variant: "error" });
    },
  });
}

export function useCreateTestRun(evalId: string) {
  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (traceIds: string[]) => {
      const res = await api.api.createTestRunApiV1ContinuousEvalsEvalIdTestRunsPost(evalId, {
        trace_ids: traceIds,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.continuousEvals.testRuns.byEval(evalId) });
    },
    onError: (error) => {
      let message = "Failed to create test run";
      if (isAxiosError(error)) {
        message = error.response?.data.detail ?? message;
      }
      enqueueSnackbar(message, { variant: "error" });
    },
  });
}

export function useTestRun(testRunId: string | undefined) {
  const api = useApi()!;

  return useQuery({
    ...testRunQueryOptions({ api, testRunId: testRunId ?? "" }),
    enabled: !!testRunId,
    refetchInterval: pollWhileInProgress((data: ContinuousEvalTestRunResponse | undefined) => data?.status, POLL_INTERVAL.FAST),
  });
}

export function useTestRunResults(testRunId: string | undefined) {
  const api = useApi()!;

  return useQuery({
    ...testRunResultsQueryOptions({ api, testRunId: testRunId ?? "", pageSize: 50 }),
    enabled: !!testRunId,
    refetchInterval: pollWhileAnyInProgress(
      (data) => data?.annotations,
      (annotation) => annotation.run_status,
      POLL_INTERVAL.FAST
    ),
  });
}
