import { SpanDrawerBody } from "@arthur/shared-components";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { useDrawerTarget } from "../hooks/useDrawerTarget";
import { useSelection } from "../hooks/useSelection";
import { usePaginationContext } from "../stores/pagination-context";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { computeSpanMetrics, getSpan } from "@/services/tracing";
import { wait } from "@/utils";

type Props = {
  id: string;
};

export const SpanDrawerContent = ({ id }: Props) => {
  const api = useApi();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [current, setDrawerTarget] = useDrawerTarget();
  const [, select] = useSelection("span");
  const paginationContext = usePaginationContext((state) => state.context);

  const { data: span } = useSuspenseQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.spans.byId(id),
    queryFn: () => getSpan(api!, { spanId: id! }),
  });

  const refreshMetrics = useMutation({
    mutationFn: async () => {
      const [, data] = await Promise.all([wait(1000), computeSpanMetrics(api!, { spanId: id! })]);

      return data;
    },
    onMutate: () => {
      track(EVENT_NAMES.TRACING_REFRESH_METRICS_CLICKED, {
        level: "span",
        span_id: id,
        trace_id: span.trace_id,
        task_id: span.task_id ?? "",
      });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.spans.byId(id), data);
      track(EVENT_NAMES.TRACING_REFRESH_METRICS_RESULT, {
        level: "span",
        span_id: id,
        trace_id: span.trace_id,
        task_id: span.task_id ?? "",
        success: true,
      });
    },
    onError: (error) => {
      track(EVENT_NAMES.TRACING_REFRESH_METRICS_RESULT, {
        level: "span",
        span_id: id,
        trace_id: span.trace_id,
        task_id: span.task_id ?? "",
        success: false,
        error_message: error instanceof Error ? error.message : "Failed to refresh metrics",
      });
    },
  });

  const handleRefreshMetrics = () => {
    refreshMetrics.mutate();
  };

  const handleOpenTraceDrawer = () => {
    select(span.span_id);
    track(EVENT_NAMES.TRACING_DRAWER_SWITCH, {
      from_level: "span",
      to_level: "trace",
      span_id: span.span_id,
      trace_id: span.trace_id,
      task_id: span.task_id ?? "",
    });
    setDrawerTarget({ target: "trace", id: span.trace_id });
  };

  const handleOpenInPlayground = (spanId: string, taskId: string) => {
    track(EVENT_NAMES.PLAYGROUND_OPEN_FROM_SPAN, {
      task_id: taskId,
      span_id: spanId,
      trace_id: span.trace_id,
      source: "span_drawer",
    });
    navigate(`/tasks/${taskId}/playgrounds/prompts?spanId=${spanId}`);
  };

  return (
    <SpanDrawerBody
      span={span as unknown as Record<string, unknown>}
      spanId={id}
      onRefreshMetrics={handleRefreshMetrics}
      isRefreshingMetrics={refreshMetrics.isPending}
      onOpenTraceDrawer={handleOpenTraceDrawer}
      onOpenPlayground={handleOpenInPlayground}
      currentTarget={current?.target ?? null}
      currentId={current?.id ?? null}
      paginationContext={paginationContext}
      onNavigate={(target, id) => setDrawerTarget({ target, id })}
    />
  );
};
