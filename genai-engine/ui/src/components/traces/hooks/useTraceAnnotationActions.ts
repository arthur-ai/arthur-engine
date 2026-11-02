import type { AnnotationEvalActions, TraceColumnDependencyOptions, TraceDrawerAnnotationBarSlotProps } from "@arthur/shared-components/traces";
import { useMemo } from "react";
import { useNavigate } from "react-router";

import { TOUR_IDS, tourDataAttr } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";
import { useTask } from "@/hooks/useTask";

const markAnnotationsReviewed = () => dispatchTourEvent(TASK_TOUR_EVENTS.annotationsReviewed);

const TRACE_DRAWER_ANNOTATION_BAR_TOUR_SLOTS: TraceDrawerAnnotationBarSlotProps = {
  annotations: tourDataAttr(TOUR_IDS.traceDrawerEvals),
  feedback: tourDataAttr(TOUR_IDS.traceDrawerFeedback),
  annotationsDialog: tourDataAttr(TOUR_IDS.traceAnnotationsModal),
  feedbackPopup: tourDataAttr(TOUR_IDS.traceFeedbackPopover),
};

const useAnnotationEvalActions = (): AnnotationEvalActions => {
  const { task } = useTask();
  const navigate = useNavigate();
  const taskId = task?.id;

  return useMemo(
    () => ({
      onViewResults: (annotation) => navigate(`/tasks/${taskId}/evaluate?id=${annotation.id}&section=results`),
      onRerun: (annotation) => navigate(`/tasks/${taskId}/evaluate?id=${annotation.id}&section=results&action=rerun`),
    }),
    [navigate, taskId]
  );
};

/** Eval links and task-tour events for the trace drawer's annotation bar. */
export const useTraceDrawerAnnotationActions = () => {
  const evalActions = useAnnotationEvalActions();

  return {
    evalActions,
    onAnnotationsDialogOpen: refreshTaskTourTarget,
    onAnnotationsReviewed: markAnnotationsReviewed,
    annotationBarSlotProps: TRACE_DRAWER_ANNOTATION_BAR_TOUR_SLOTS,
  };
};

/** The same wiring for the annotation cell in trace tables. */
export const useAnnotationCellOptions = (): NonNullable<TraceColumnDependencyOptions["annotationCell"]> => {
  const evalActions = useAnnotationEvalActions();

  return useMemo(
    () => ({
      evalActions,
      onDialogOpen: refreshTaskTourTarget,
      onReviewed: markAnnotationsReviewed,
      slotProps: { dialogPaper: tourDataAttr(TOUR_IDS.traceAnnotationsModal) },
    }),
    [evalActions]
  );
};
