import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useSnackbar } from "notistack";
import { useEffect, useState } from "react";

import { annotationQueryOptions } from "./useAnnotation";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  onSuccess?: () => void;
  annotationId: string;
  rerunOnMount?: boolean;
};

const REFRESH_INTERVAL = 2_000;

export const useRerunContinuousEval = ({ onSuccess, annotationId, rerunOnMount = false }: Opts) => {
  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();
  const { task } = useTask();

  const queryClient = useQueryClient();

  const [running, setRunning] = useState(() => rerunOnMount);

  const annotationQuery = useQuery({
    ...annotationQueryOptions({
      api,
      annotationId,
    }),
    enabled: !!annotationId && running,
    refetchInterval: (query) => {
      if (query.state.data?.data.run_status === "pending") return REFRESH_INTERVAL;
      return false;
    },
  });

  useEffect(() => {
    const status = annotationQuery.data?.run_status;

    if (status === "pending") return;

    setRunning(false);
    queryClient.invalidateQueries({ queryKey: [queryKeys.annotations.byId(annotationId)] });
    queryClient.invalidateQueries({ queryKey: [queryKeys.continuousEvals.results(task!.id)] });
    queryClient.invalidateQueries({ queryKey: [queryKeys.traces.list], exact: false });
  }, [annotationId, annotationQuery.data, queryClient, task]);

  const mutation = useMutation({
    mutationFn: async (annotationId: string) => {
      return api.api.rerunContinuousEvalApiV1ContinuousEvalsResultsRunIdRerunPost(annotationId);
    },
    onSuccess: () => {
      onSuccess?.();
      setRunning(true);
    },
    onError: (error) => {
      let message = "Failed to rerun continuous eval";

      if (isAxiosError(error)) {
        message = error.response?.data.detail ?? message;
      }

      enqueueSnackbar(message, { variant: "error" });
    },
  });

  useEffect(() => {
    if (rerunOnMount && !mutation.isPending) mutation.mutate(annotationId);
  }, [mutation.mutate, mutation.isPending, rerunOnMount, annotationId]);

  return {
    mutate: mutation.mutate,
    isPending: mutation.isPending || running,
  };
};
