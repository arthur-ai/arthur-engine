import { type TraceDrawerBodySlotProps, TraceDrawerView } from "@arthur/shared-components";
import { Skeleton } from "@mui/material";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useEffectEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { useDrawerTarget } from "../hooks/useDrawerTarget";
import { useSelection } from "../hooks/useSelection";
import { useTraceDrawerAnnotationActions } from "../hooks/useTraceAnnotationActions";
import { useTraceFeedback } from "../hooks/useTraceFeedback";
import { usePaginationContext } from "../stores/pagination-context";
import { flattenSpans } from "../utils/spans";

import { AddToDatasetDrawer } from "./add-to-dataset/Drawer";
import { ContinuousEvalDrawer } from "./continuous-eval/ContinuousEvalDrawer";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";
import { track } from "@/services/analytics";
import { computeTraceMetrics, getTrace } from "@/services/tracing";
import { wait } from "@/utils";

type Props = {
  id: string;
};

export const TraceDrawerContent = ({ id }: Props) => {
  const { task } = useTask();
  const queryClient = useQueryClient();

  const api = useApi();
  const [selectedSpanId, select] = useSelection("span");
  const [current, setDrawerTarget] = useDrawerTarget();
  const navigate = useNavigate();
  const paginationContext = usePaginationContext((state) => state.context);
  const feedback = useTraceFeedback(id);
  const annotationActions = useTraceDrawerAnnotationActions();

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  const { data: trace } = useSuspenseQuery({
    queryKey: queryKeys.traces.byId(id),
    queryFn: () => getTrace(api!, { traceId: id! }),
  });

  const refreshMetrics = useMutation({
    mutationFn: async () => {
      const [, data] = await Promise.all([wait(1000), computeTraceMetrics(api!, { traceId: id! })]);

      return data;
    },
    onMutate: () => {
      track("tracing/refresh_metrics_clicked", {
        level: "trace",
        trace_id: id,
        task_id: task?.id ?? "",
      });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.traces.byId(id), data);
      track("tracing/refresh_metrics_result", {
        level: "trace",
        trace_id: id,
        task_id: task?.id ?? "",
        success: true,
      });
    },
    onError: (error) => {
      track("tracing/refresh_metrics_result", {
        level: "trace",
        trace_id: id,
        task_id: task?.id ?? "",
        success: false,
        error_message: error instanceof Error ? error.message : "Failed to refresh metrics",
      });
    },
  });

  // Flatten nested spans recursively
  const flatSpans = useMemo(() => flattenSpans(trace?.root_spans ?? []), [trace]);

  const rootSpan = trace?.root_spans?.[0];

  const onOpenDrawer = useEffectEvent(() => {
    if (!trace?.root_spans?.length || !rootSpan) return;

    if (!selectedSpanId) {
      select(rootSpan.span_id, { history: "replace" });
    }

    if (flatSpans.findIndex((span) => span.span_id === selectedSpanId) === -1) {
      select(rootSpan.span_id, { history: "replace" });
    }
  });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(onOpenDrawer, []);

  const handleRefreshMetrics = () => {
    refreshMetrics.mutate();
  };

  const handleAddToDataset = () => {
    track("dataset/add_to_dataset_started", {
      task_id: task?.id ?? "",
      trace_id: id,
      source: "trace_actions",
    });
  };

  const handleOpenContinuousEvals = (traceId: string, taskId: string) => {
    track("continuous_evals/new_from_trace", {
      task_id: taskId,
      trace_id: traceId,
      source: "trace_actions",
    });
    setContinuousEvalOpen(true);
  };

  const [addToDatasetOpen, setAddToDatasetOpen] = useState(false);
  const [continuousEvalOpen, setContinuousEvalOpen] = useState(false);

  const handleSelectSpan = useCallback(
    (spanId: string | null) => {
      if (!spanId) return;
      select(spanId);
      dispatchTourEvent(TASK_TOUR_EVENTS.spansReviewed);
    },
    [select]
  );

  // There is no `actions` slot: the tour finds the Trace Actions dropdown by its button label in `TracesTargetWidget`.
  const tourSlotProps = useMemo<TraceDrawerBodySlotProps>(
    () => ({
      root: { "data-tour-id": TOUR_IDS.traceDrawerAddToDataset },
      spans: {
        "data-tour-id": TOUR_IDS.traceDrawerSpans,
        onClick: () => dispatchTourEvent(TASK_TOUR_EVENTS.spansReviewed),
      },
    }),
    []
  );

  if (!trace) return null;

  return (
    <TraceDrawerView
      trace={trace}
      traceId={id}
      selectedSpanId={selectedSpanId}
      onSelectSpan={handleSelectSpan}
      onRefreshMetrics={handleRefreshMetrics}
      isRefreshingMetrics={refreshMetrics.isPending}
      onAddToDataset={() => {
        handleAddToDataset();
        setAddToDatasetOpen(true);
        dispatchTourEvent(TASK_TOUR_EVENTS.traceAddToDatasetOpened);
      }}
      onOpenSpanDrawer={(spanId) => setDrawerTarget({ target: "span", id: spanId })}
      onOpenPlayground={(spanId, taskId) => navigate(`/tasks/${taskId}/playgrounds/prompts?spanId=${spanId}`)}
      taskId={task?.id}
      onOpenContinuousEvals={handleOpenContinuousEvals}
      currentTarget={current?.target ?? null}
      currentId={current?.id ?? null}
      paginationContext={paginationContext}
      onNavigate={(target, navId) => setDrawerTarget({ target, id: navId })}
      slotProps={tourSlotProps}
      feedback={feedback}
      {...annotationActions}
      renderAfterDrawer={() => (
        <>
          <AddToDatasetDrawer traceId={id} open={addToDatasetOpen} onClose={() => setAddToDatasetOpen(false)} />
          <ContinuousEvalDrawer traceId={id} open={continuousEvalOpen} onClose={() => setContinuousEvalOpen(false)} />
        </>
      )}
    />
  );
};

export const TraceContentSkeleton = () => {
  return (
    <Stack spacing={2} sx={{ height: "100%" }}>
      <Stack
        direction="row"
        spacing={2}
        sx={{
          justifyContent: "space-between",
          alignItems: "center",
          px: 4,
          py: 2,
          backgroundColor: "action.hover",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="column" spacing={1}>
          <Skeleton variant="text" width={100} height={20} />
          <Skeleton variant="text" width={200} height={32} />
        </Stack>

        <Skeleton variant="rounded" width={200} height={32} sx={{ borderRadius: 16 }} />
      </Stack>

      <Box sx={{ flexGrow: 1, p: 4 }}>
        <Skeleton variant="rectangular" height="100%" sx={{ borderRadius: 1 }} />
      </Box>
    </Stack>
  );
};
