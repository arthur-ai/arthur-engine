import { TraceDrawerBody } from "@arthur/shared-components";
import { Skeleton } from "@mui/material";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useDrawerTarget } from "../hooks/useDrawerTarget";
import { useSelection } from "../hooks/useSelection";
import { usePaginationContext } from "../stores/pagination-context";
import { flattenSpans } from "../utils/spans";

import { AddToDatasetDrawer } from "./add-to-dataset/Drawer";
import { AnnotationCell } from "./AnnotationCell";
import { FeedbackPanel } from "./feedback/FeedbackPanel";

import { CreateContinuousEvalDialog } from "@/components/live-evals/components/create-form";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
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
      track(EVENT_NAMES.TRACING_REFRESH_METRICS_CLICKED, {
        level: "trace",
        trace_id: id,
        task_id: task?.id ?? "",
      });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["trace", id], data);
      track(EVENT_NAMES.TRACING_REFRESH_METRICS_RESULT, {
        level: "trace",
        trace_id: id,
        task_id: task?.id ?? "",
        success: true,
      });
    },
    onError: (error) => {
      track(EVENT_NAMES.TRACING_REFRESH_METRICS_RESULT, {
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
    track(EVENT_NAMES.DATASET_ADD_TO_DATASET_STARTED, {
      task_id: task?.id ?? "",
      trace_id: id,
      source: "trace_actions",
    });
  };

  const handleOpenContinuousEvals = (traceId: string, taskId: string) => {
    track(EVENT_NAMES.CONTINUOUS_EVALS_NEW_FROM_TRACE, {
      task_id: taskId,
      trace_id: traceId,
      source: "trace_actions",
    });
    setCreateEvalOpen(true);
  };

  const [addToDatasetOpen, setAddToDatasetOpen] = useState(false);
  const [createEvalOpen, setCreateEvalOpen] = useState(false);

  if (!trace) return null;

  return (
    <TraceDrawerBody
      trace={trace}
      traceId={id}
      selectedSpanId={selectedSpanId}
      onSelectSpan={select}
      onRefreshMetrics={handleRefreshMetrics}
      isRefreshingMetrics={refreshMetrics.isPending}
      onAddToDataset={() => {
        handleAddToDataset();
        setAddToDatasetOpen(true);
      }}
      onOpenSpanDrawer={(spanId) => setDrawerTarget({ target: "span", id: spanId })}
      onOpenPlayground={(spanId, taskId) => navigate(`/tasks/${taskId}/playgrounds/prompts?spanId=${spanId}`)}
      taskId={task?.id}
      onOpenContinuousEvals={handleOpenContinuousEvals}
      currentTarget={current?.target ?? null}
      currentId={current?.id ?? null}
      paginationContext={paginationContext}
      onNavigate={(target, navId) => setDrawerTarget({ target, id: navId })}
      renderAnnotationBar={({ annotations, traceId: tid, containerRef }) => (
        <>
          <AnnotationCell annotations={(annotations ?? []) as AgenticAnnotationResponse[]} traceId={tid} />
          <FeedbackPanel containerRef={containerRef} annotations={(annotations ?? []) as AgenticAnnotationResponse[]} traceId={tid} />
        </>
      )}
      renderAfterDrawer={() => (
        <>
          <AddToDatasetDrawer traceId={id} open={addToDatasetOpen} onClose={() => setAddToDatasetOpen(false)} />
          {task?.id && <CreateContinuousEvalDialog open={createEvalOpen} onClose={() => setCreateEvalOpen(false)} taskId={task.id} />}
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
