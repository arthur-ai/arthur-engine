import { type GetSpanDetailsStrategy, type TraceDrawerBodySlotProps, TraceDrawerBody } from "@arthur/shared-components";
import { Skeleton } from "@mui/material";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useEffectEvent, useMemo, useState, type RefObject } from "react";
import { useNavigate } from "react-router-dom";

import { getSpanDetailsStrategy } from "../data/details-strategy";
import { useDrawerTarget } from "../hooks/useDrawerTarget";
import { useSelection } from "../hooks/useSelection";
import { usePaginationContext } from "../stores/pagination-context";
import { extractGuardrailInvocations } from "../utils/guardrails";
import { flattenSpans } from "../utils/spans";

import { AddToDatasetDrawer } from "./add-to-dataset/Drawer";
import { ContinuousEvalDrawer } from "./continuous-eval/ContinuousEvalDrawer";
import { GuardrailSummaryBar } from "./guardrail-bar/GuardrailSummaryBar";
import { TraceDrawerAnnotationBar } from "./TraceDrawerAnnotationBar";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
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

  const { data: trace } = useSuspenseQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
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
      queryClient.setQueryData(["trace", id], data);
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

  const guardrailInvocations = useMemo(() => extractGuardrailInvocations(trace?.root_spans ?? []), [trace]);

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

  const handleJumpToSpan = useCallback(
    (spanId: string, containerRef: RefObject<HTMLDivElement | null>) => {
      handleSelectSpan(spanId);
      // The span tree is rendered inside the compiled drawer body: selecting a
      // span marks its row with `data-selected` but does not scroll it into
      // view. Best-effort scroll after the selection re-render, scoped to the
      // spans column via its tour-id anchor.
      requestAnimationFrame(() => {
        const spansColumn = containerRef.current?.querySelector(`[data-tour-id="${TOUR_IDS.traceDrawerSpans}"]`);
        spansColumn?.querySelector("[data-selected]")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    },
    [handleSelectSpan]
  );

  // Task-tour anchors. `TraceDrawerBody`'s `slotProps` spreads each entry onto
  // a wrapping `<div>` inside the drawer, so we can attach `data-tour-id`
  // without resorting to opaque DOM wrappers. There is no `actions` slot — the
  // Trace Actions dropdown is resolved by its button label in
  // `TracesTargetWidget` instead.
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
    <TraceDrawerBody
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
      renderAnnotationBar={({ annotations, traceId: tid, containerRef }) => (
        <TraceDrawerAnnotationBar annotations={(annotations ?? []) as AgenticAnnotationResponse[]} traceId={tid} containerRef={containerRef} />
      )}
      renderBelowAnnotationBar={({ containerRef }) => (
        <GuardrailSummaryBar
          invocations={guardrailInvocations}
          selectedSpanId={selectedSpanId}
          onJumpToSpan={(spanId) => handleJumpToSpan(spanId, containerRef)}
        />
      )}
      renderAfterDrawer={() => (
        <>
          <AddToDatasetDrawer traceId={id} open={addToDatasetOpen} onClose={() => setAddToDatasetOpen(false)} />
          <ContinuousEvalDrawer traceId={id} open={continuousEvalOpen} onClose={() => setContinuousEvalOpen(false)} />
        </>
      )}
      getSpanDetailsStrategy={getSpanDetailsStrategy as GetSpanDetailsStrategy}
    />
  );
};

export const TraceContentSkeleton = () => {
  return (
    <Stack spacing={2} sx={{ height: "100%" }}>
      <Stack
        direction="row"
        spacing={2}
        justifyContent="space-between"
        alignItems="center"
        sx={{
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
