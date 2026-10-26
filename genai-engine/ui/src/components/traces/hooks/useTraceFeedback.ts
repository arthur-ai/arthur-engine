import type { FeedbackPanelHandlers, TraceFeedback } from "@arthur/shared-components";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";

import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";
import { useApi } from "@/hooks/useApi";
import type { AgenticAnnotationResponse, TraceResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { track } from "@/services/analytics";

const toFeedbackType = (score: TraceFeedback["score"]) => (score === 1 ? "positive" : "negative");

const getErrorMessage = (error: unknown, fallback: string) => (error instanceof Error ? error.message : fallback);

/** Writes the trace's human feedback, with optimistic updates of the cached trace. */
export const useTraceFeedback = (traceId: string): FeedbackPanelHandlers => {
  const api = useApi()!;
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const traceKey = queryKeys.traces.byId(traceId);

  const updateCachedTrace = async (update: (trace: TraceResponse) => TraceResponse) => {
    await queryClient.cancelQueries({ queryKey: traceKey });
    const previousTrace = queryClient.getQueryData<TraceResponse>(traceKey);
    if (previousTrace) queryClient.setQueryData(traceKey, update(previousTrace));
    return { previousTrace };
  };

  const refetchTraces = () => {
    queryClient.invalidateQueries({ queryKey: traceKey });
    queryClient.invalidateQueries({ queryKey: queryKeys.traces.list });
  };

  const submitFeedback = useMutation({
    mutationFn: async ({ score, description }: TraceFeedback) => {
      await api.api.annotateTraceApiV1TracesTraceIdAnnotationsPost(traceId, {
        annotation_score: score,
        annotation_description: description,
      });
    },
    onMutate: ({ score, description }) =>
      updateCachedTrace((trace) => ({
        ...trace,
        annotations: [
          ...(trace.annotations ?? []),
          { annotation_type: "human", annotation_score: score, annotation_description: description } as AgenticAnnotationResponse,
        ],
      })),
    onSuccess: (_, { score, description }) => {
      enqueueSnackbar("Feedback submitted", { variant: "success" });
      dispatchTourEvent(TASK_TOUR_EVENTS.feedbackAdded);
      track("feedback/submitted", {
        trace_id: traceId,
        feedback_type: toFeedbackType(score),
        details_length: description.length,
        success: true,
      });
    },
    onError: (error, { score }, context) => {
      queryClient.setQueryData(traceKey, context?.previousTrace);
      enqueueSnackbar("Failed to submit feedback", { variant: "error" });
      track("feedback/error", {
        trace_id: traceId,
        feedback_type: toFeedbackType(score),
        error_message: getErrorMessage(error, "Failed to submit feedback"),
      });
    },
    onSettled: refetchTraces,
  });

  const clearFeedback = useMutation({
    mutationFn: () => api.api.deleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDelete(traceId),
    onMutate: () =>
      updateCachedTrace((trace) => ({
        ...trace,
        annotations: trace.annotations?.filter((annotation) => annotation.annotation_type !== "human"),
      })),
    onSuccess: () => {
      enqueueSnackbar("Feedback cleared", { variant: "success" });
      track("feedback/cleared", { trace_id: traceId });
    },
    onError: (error, _, context) => {
      queryClient.setQueryData(traceKey, context?.previousTrace);
      enqueueSnackbar("Failed to clear feedback", { variant: "error" });
      track("feedback/error", {
        trace_id: traceId,
        error_message: getErrorMessage(error, "Failed to clear feedback"),
      });
    },
    onSettled: refetchTraces,
  });

  return {
    onSubmit: submitFeedback.mutateAsync,
    onClear: clearFeedback.mutateAsync,
    onOpen: (feedbackType) => {
      refreshTaskTourTarget();
      track("feedback/opened", { trace_id: traceId, feedback_type: feedbackType });
    },
  };
};
