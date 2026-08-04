import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { Box, Button, CircularProgress, Drawer, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import { QueryErrorResetBoundary, useSuspenseQuery } from "@tanstack/react-query";
import { Suspense, useMemo, useState } from "react";
import { ErrorBoundary } from "react-error-boundary";
import { Link as RouterLink } from "react-router";

import { CopyableChip } from "@/components/common";
import { traceDeepLinkPath } from "@/components/common/SourceTraceLink";
import { SpanDetails, SpanDetailsHeader, SpanDetailsPanels, SpanDetailsWidgets } from "@/components/traces/components/SpanDetails";
import { SpanTree } from "@/components/traces/components/SpanTree";
import { getSpanDetailsStrategy } from "@/components/traces/data/details-strategy";
import { flattenSpans } from "@/components/traces/utils/spans";
import { useApi } from "@/hooks/useApi";
import type { NestedSpanWithMetricsResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { getTrace } from "@/services/tracing";

type Props = {
  open: boolean;
  onClose: () => void;
  traceId: string;
  taskId: string;
};

/**
 * Stripped-down in-place trace viewer: span tree + span details, with a link
 * to the full trace page. Opened from surfaces that show a record's source
 * trace (dataset rows, prompt-experiment test cases).
 */
export const SourceTraceDrawer = ({ open, onClose, traceId, taskId }: Props) => {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      anchor="right"
      // Drawers default to zIndex.drawer (1200); some launch sites are inside Modals/Dialogs (1300).
      sx={{ zIndex: (theme) => theme.zIndex.modal + 1 }}
      slotProps={{ paper: { sx: { width: "85%" } } }}
    >
      {open && (
        <Stack direction="column" sx={{ height: "100%" }}>
          <SourceTraceDrawerHeader traceId={traceId} taskId={taskId} onClose={onClose} />
          <QueryErrorResetBoundary>
            {({ reset }) => (
              <ErrorBoundary
                onReset={reset}
                resetKeys={[traceId]}
                fallbackRender={({ resetErrorBoundary }) => <SourceTraceErrorState onRetry={resetErrorBoundary} />}
              >
                <Suspense
                  fallback={
                    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", flex: 1 }}>
                      <CircularProgress />
                    </Box>
                  }
                >
                  <SourceTraceDrawerContent key={traceId} traceId={traceId} />
                </Suspense>
              </ErrorBoundary>
            )}
          </QueryErrorResetBoundary>
        </Stack>
      )}
    </Drawer>
  );
};

const SourceTraceDrawerHeader = ({ traceId, taskId, onClose }: { traceId: string; taskId: string; onClose: () => void }) => (
  <Stack
    direction="row"
    alignItems="center"
    justifyContent="space-between"
    sx={{ px: 2, py: 1, borderBottom: 1, borderColor: "divider", backgroundColor: "background.paper" }}
  >
    <Stack direction="row" alignItems="center" gap={1}>
      <Typography variant="subtitle1" fontWeight={600} color="text.primary">
        Source trace
      </Typography>
      <CopyableChip label={traceId} size="small" sx={{ fontFamily: "monospace" }} />
    </Stack>
    <Stack direction="row" alignItems="center" gap={1}>
      <Button
        component={RouterLink}
        to={traceDeepLinkPath(taskId, traceId)}
        target="_blank"
        rel="noopener noreferrer"
        variant="outlined"
        size="small"
        startIcon={<OpenInNewIcon />}
      >
        Open full trace
      </Button>
      <Tooltip title="Close">
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Tooltip>
    </Stack>
  </Stack>
);

const SourceTraceDrawerContent = ({ traceId }: { traceId: string }) => {
  const api = useApi();

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  const { data: trace } = useSuspenseQuery({
    queryKey: queryKeys.traces.byId(traceId),
    queryFn: () => getTrace(api!, { traceId }),
  });

  const rootSpans = useMemo(() => trace?.root_spans ?? [], [trace]);
  const flatSpans = useMemo(() => flattenSpans(rootSpans), [rootSpans]);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(rootSpans[0]?.span_id ?? null);
  const selectedSpan = useMemo(() => flatSpans.find((s) => s.span_id === selectedSpanId) ?? null, [flatSpans, selectedSpanId]);

  if (rootSpans.length === 0) {
    return <CenteredMessage>No spans found for this trace.</CenteredMessage>;
  }

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "2fr 3fr", flex: 1, minHeight: 0, overflow: "hidden" }}>
      <Box sx={{ borderRight: 1, borderColor: "divider", backgroundColor: "action.hover", overflow: "auto", p: 2 }}>
        <SpanTree spans={rootSpans} selectedSpanId={selectedSpanId} onSelectSpan={setSelectedSpanId} />
      </Box>
      <Box sx={{ overflow: "auto", p: 2 }}>
        {selectedSpan ? <SpanContentView span={selectedSpan} /> : <CenteredMessage>Select a span to view its details</CenteredMessage>}
      </Box>
    </Box>
  );
};

const SpanContentView = ({ span }: { span: NestedSpanWithMetricsResponse }) => {
  const strategy = getSpanDetailsStrategy(span.span_kind as OpenInferenceSpanKind);

  if (!strategy) {
    return <CenteredMessage>No details available for this span type.</CenteredMessage>;
  }

  return (
    <SpanDetails span={span}>
      <SpanDetailsHeader />
      <SpanDetailsWidgets />
      <SpanDetailsPanels />
    </SpanDetails>
  );
};

const SourceTraceErrorState = ({ onRetry }: { onRetry: () => void }) => (
  <Stack alignItems="center" justifyContent="center" gap={2} sx={{ flex: 1, p: 3 }}>
    <Typography variant="body2" color="text.secondary" textAlign="center">
      This trace could not be loaded. It may have been deleted or expired.
    </Typography>
    <Button variant="outlined" size="small" onClick={onRetry}>
      Retry
    </Button>
  </Stack>
);

const CenteredMessage = ({ children }: { children: React.ReactNode }) => (
  <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%", p: 3 }}>
    <Typography variant="body2" color="text.secondary">
      {children}
    </Typography>
  </Box>
);
