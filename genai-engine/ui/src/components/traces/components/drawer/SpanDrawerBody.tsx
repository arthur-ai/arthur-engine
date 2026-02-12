import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import RefreshIcon from "@mui/icons-material/Refresh";
import { Box, Button, ButtonGroup, Stack, Typography } from "@mui/material";

import { isSpanOfType } from "../../utils/spans";
import { DrawerPagination } from "../DrawerPagination";
import { SpanStatusBadge } from "../span-status-badge";
import { SpanDetails, SpanDetailsPanels, SpanDetailsWidgets } from "../SpanDetails";

import { CopyableChip } from "@/components/common";
import { NestedSpanWithMetricsResponse } from "@/lib/api";

type SpanDrawerBodyProps = {
  span: NestedSpanWithMetricsResponse;
  spanId: string;
  onRefreshMetrics?: () => void;
  isRefreshingMetrics?: boolean;
  onOpenTraceDrawer?: () => void;
  onOpenPlayground?: (spanId: string, taskId: string) => void;
  currentTarget?: "trace" | "span" | "session" | "user" | null;
  currentId?: string | null;
  paginationContext?: {
    type: "trace" | "span" | "session" | "user" | null;
    ids: string[];
  };
  onNavigate?: (target: "trace" | "span" | "session" | "user", id: string) => void;
};

export const SpanDrawerBody = ({
  span,
  spanId,
  onRefreshMetrics,
  isRefreshingMetrics = false,
  onOpenTraceDrawer,
  onOpenPlayground,
  currentTarget,
  currentId,
  paginationContext,
  onNavigate,
}: SpanDrawerBodyProps) => {
  const isLLM = isSpanOfType(span, OpenInferenceSpanKind.LLM);

  const handleOpenInPlayground = () => {
    if (span.task_id) {
      onOpenPlayground?.(span.span_id, span.task_id);
    }
  };

  return (
    <Stack spacing={0} sx={{ height: "100%" }}>
      <Stack
        direction="row"
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
        <Stack direction="column" width="100%">
          <Typography variant="body2" color="text.secondary">
            Span Details
          </Typography>
          <Stack direction="row" gap={2} alignItems="center">
            <Typography variant="h6" color="text.primary" fontWeight={700}>
              {span.span_name}
            </Typography>
            <SpanStatusBadge status={span.status_code ?? "Unset"} />
            <div className="flex-1" />
            <CopyableChip
              label={spanId}
              sx={{
                fontFamily: "monospace",
              }}
            />
          </Stack>
          <Typography variant="body2" color="text.secondary">
            Part of trace{" "}
            <Button variant="text" size="small" color="primary" sx={{ fontFamily: "monospace" }} onClick={onOpenTraceDrawer}>
              {span.trace_id}
            </Button>
          </Typography>
        </Stack>

        <Stack direction="column" spacing={1} alignItems="flex-end">
          <Stack direction="row" spacing={0} sx={{ marginLeft: "auto" }}>
            {isLLM && (
              <ButtonGroup variant="outlined" size="small" disableElevation>
                <Button onClick={handleOpenInPlayground} disabled={!span.task_id} startIcon={<OpenInNewIcon />}>
                  Open in Playground
                </Button>
                <Button loading={isRefreshingMetrics} onClick={onRefreshMetrics} startIcon={<RefreshIcon />}>
                  Refresh Metrics
                </Button>
              </ButtonGroup>
            )}
          </Stack>
        </Stack>
      </Stack>

      <Box sx={{ px: 4, py: 2, borderBottom: "1px solid", borderColor: "divider", backgroundColor: "action.selected" }}>
        {currentTarget && currentId && paginationContext && onNavigate && (
          <DrawerPagination
            currentTarget={currentTarget}
            currentId={currentId}
            contextType={paginationContext.type}
            contextIds={paginationContext.ids}
            onNavigate={onNavigate}
          />
        )}
      </Box>

      <Box sx={{ overflow: "auto", maxHeight: "100%", px: 4, py: 2 }}>
        <SpanDetails span={span}>
          <SpanDetailsWidgets />
          <SpanDetailsPanels />
        </SpanDetails>
      </Box>
    </Stack>
  );
};
