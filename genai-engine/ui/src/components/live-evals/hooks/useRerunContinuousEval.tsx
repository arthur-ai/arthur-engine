import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useSnackbar } from "notistack";
import { useEffect, useEffectEvent, useRef, useState } from "react";

import { annotationQueryOptions } from "./useAnnotation";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { pollWhileInProgress, POLL_INTERVAL } from "@/lib/polling";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  onSuccess?: () => void;
  annotationId: string;
  rerunOnMount?: boolean;
};

export const useRerunContinuousEval = ({ onSuccess, annotationId, rerunOnMount = false }: Opts) => {
  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();
  const { task } = useTask();

  const queryClient = useQueryClient();

  const [running, setRunning] = useState(false);

  const hasAutoTriggeredRef = useRef(false);

  const annotationQuery = useQuery({
    ...annotationQueryOptions({
      api,
      annotationId,
    }),
    enabled: !!annotationId && running,
    refetchInterval: pollWhileInProgress((data) => data?.data.run_status, POLL_INTERVAL.FAST),
  });

  const handleDone = useEffectEvent(() => {
    setRunning(false);
    queryClient.invalidateQueries({ queryKey: [queryKeys.annotations.byId(annotationId)] });
    queryClient.invalidateQueries({ queryKey: [queryKeys.continuousEvals.results(task!.id)] });
    queryClient.invalidateQueries({ queryKey: [queryKeys.traces.list], exact: false });
  });

  useEffect(() => {
    const status = annotationQuery.data?.run_status;
    if (!status || status === "pending") return;

    handleDone();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [annotationQuery.data]);

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

  const runFromAutoTrigger = useEffectEvent(() => {
    mutation.mutate(annotationId);
  });

  useEffect(() => {
    if (!rerunOnMount) return;
    if (!annotationId) return;
    if (hasAutoTriggeredRef.current) return;

    hasAutoTriggeredRef.current = true;

    runFromAutoTrigger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rerunOnMount, annotationId]);

  return {
    mutate: mutation.mutate,
    isPending: mutation.isPending || running,
  };
};
