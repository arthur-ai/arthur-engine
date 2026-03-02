import { Menu } from "@base-ui/react/menu";
import AddIcon from "@mui/icons-material/Add";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import RefreshIcon from "@mui/icons-material/Refresh";
import TroubleshootIcon from "@mui/icons-material/Troubleshoot";
import { Button, List, ListItemButton, ListItemText, Paper } from "@mui/material";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import React, { useMemo, useRef, useState } from "react";

import { BucketProvider } from "../../context/bucket-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { flattenSpans, getSpanDuration } from "../../utils/spans";
import { AddToDatasetDrawer } from "../add-to-dataset/Drawer";
import { AnnotationCell } from "../AnnotationCell";
import { DrawerPagination } from "../DrawerPagination";
import { FeedbackPanel } from "../feedback/FeedbackPanel";
import { SpanDetails, SpanDetailsHeader, SpanDetailsPanels, SpanDetailsWidgets } from "../SpanDetails";
import { SpanTree } from "../SpanTree";

import { CopyableChip } from "@/components/common";
import { CreateContinuousEvalDialog } from "@/components/live-evals/components/create-form";
import { TraceResponse } from "@/lib/api-client/api-client";

type TraceDrawerBodyProps = {
  trace: TraceResponse;
  traceId: string;
  selectedSpanId: string | null;
  onSelectSpan: (spanId: string | null) => void;
  onRefreshMetrics?: () => void;
  isRefreshingMetrics?: boolean;
  onAddToDataset?: () => void;
  onOpenSpanDrawer?: (spanId: string) => void;
  onOpenPlayground?: (spanId: string, taskId: string) => void;
  taskId?: string;
  onOpenContinuousEvals?: (traceId: string, taskId: string) => void;
  currentTarget?: "trace" | "span" | "session" | "user" | null;
  currentId?: string | null;
  paginationContext?: {
    type: "trace" | "span" | "session" | "user" | null;
    ids: string[];
  };
  onNavigate?: (target: "trace" | "span" | "session" | "user", id: string) => void;
};

export const TraceDrawerBody = ({
  trace,
  traceId,
  selectedSpanId,
  onSelectSpan,
  onRefreshMetrics,
  isRefreshingMetrics = false,
  onAddToDataset,
  onOpenSpanDrawer,
  onOpenPlayground,
  taskId,
  onOpenContinuousEvals,
  currentTarget,
  currentId,
  paginationContext,
  onNavigate,
}: TraceDrawerBodyProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [addToDatasetOpen, setAddToDatasetOpen] = useState(false);
  const [createEvalOpen, setCreateEvalOpen] = useState(false);

  const name =
    trace?.root_spans?.length === 1
      ? trace.root_spans[0].span_name
      : trace?.root_spans && trace.root_spans.length > 1
        ? `${trace.root_spans[0].span_name} (+${trace.root_spans.length - 1} more root${trace.root_spans.length > 2 ? "s" : ""})`
        : undefined;

  // Flatten nested spans recursively
  const flatSpans = useMemo(() => flattenSpans(trace?.root_spans ?? []), [trace]);

  const thresholds = useMemo(() => buildThresholdsFromSample(flatSpans.map((span) => getSpanDuration(span) ?? 0)), [flatSpans]);

  const selectedSpan = flatSpans.find((span) => span.span_id === selectedSpanId);

  const handleAddToDataset = () => {
    onAddToDataset?.();
    setAddToDatasetOpen(true);
  };

  const handleCreateContinuousEval = () => {
    if (taskId) onOpenContinuousEvals?.(traceId, taskId);
    setCreateEvalOpen(true);
  };

  return (
    <BucketProvider thresholds={thresholds}>
      <Stack spacing={0} sx={{ height: "100%" }} ref={containerRef}>
        <Stack
          direction="row"
          spacing={0}
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
          <Stack direction="column" gap={0}>
            <Typography variant="body2" color="text.secondary">
              Trace Details
            </Typography>
            <Stack direction="row" gap={2}>
              <Typography variant="h5" color="text.primary" fontWeight="bold">
                {name}
              </Typography>
              <CopyableChip
                label={traceId}
                sx={{
                  fontFamily: "monospace",
                }}
              />
            </Stack>
          </Stack>

          <Stack gap={1} alignItems="center" direction="row">
            <Menu.Root>
              <Menu.Trigger render={<Button variant="contained" size="small" endIcon={<ArrowDropDownIcon />} loading={isRefreshingMetrics} />}>
                Trace Actions
              </Menu.Trigger>
              <Menu.Portal keepMounted container={containerRef.current}>
                <Menu.Positioner sideOffset={8} side="bottom" align="center">
                  <Menu.Popup render={<List component={Paper} dense className="outline-none origin-(--transform-origin)" />}>
                    <Menu.Item render={<ListItemButton onClick={onRefreshMetrics} />}>
                      <RefreshIcon sx={{ mr: 1, fontSize: 16 }} />
                      <ListItemText primary="Refresh Metrics" />
                    </Menu.Item>
                    <Menu.Item render={<ListItemButton onClick={handleAddToDataset} />}>
                      <AddIcon sx={{ mr: 1, fontSize: 16 }} />
                      <ListItemText primary="Add to Dataset" secondary="Add this trace to a dataset" />
                    </Menu.Item>
                    <Menu.Separator />
                    {taskId && onOpenContinuousEvals && (
                      <Menu.Item render={<ListItemButton onClick={handleCreateContinuousEval} />}>
                        <TroubleshootIcon sx={{ mr: 1, fontSize: 16 }} />
                        <ListItemText primary="Evaluate Traces Like This" secondary="Evaluate traces that are similar to this one" />
                      </Menu.Item>
                    )}
                  </Menu.Popup>
                </Menu.Positioner>
              </Menu.Portal>
            </Menu.Root>
          </Stack>
        </Stack>

        <Stack
          direction="row"
          alignItems="center"
          gap={2}
          sx={{ px: 4, py: 2, borderBottom: "1px solid", borderColor: "divider", backgroundColor: "action.selected" }}
        >
          {currentTarget && currentId && paginationContext && onNavigate && (
            <DrawerPagination
              currentTarget={currentTarget}
              currentId={currentId}
              contextType={paginationContext.type}
              contextIds={paginationContext.ids}
              onNavigate={onNavigate}
            />
          )}
          <Box sx={{ flex: 1 }} />
          {trace.annotations && trace.annotations.length > 0 && <AnnotationCell annotations={trace.annotations} traceId={traceId} />}
          <FeedbackPanel containerRef={containerRef} annotations={trace.annotations} traceId={traceId} />
        </Stack>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "2fr 3fr",
            gap: 0,
            height: "100%",
            overflow: "auto",
          }}
        >
          <Box
            sx={{
              borderRight: "1px solid",
              borderColor: "divider",
              p: 2,
              backgroundColor: "action.hover",
              overflow: "auto",
              maxHeight: "100%",
            }}
          >
            {trace?.root_spans && <SpanTree spans={trace.root_spans} selectedSpanId={selectedSpanId} onSelectSpan={onSelectSpan} />}
          </Box>
          <Box sx={{ overflow: "auto", maxHeight: "100%", p: 2 }}>
            {selectedSpan && (
              <SpanDetails span={selectedSpan}>
                <SpanDetailsHeader onOpenSpanDrawer={onOpenSpanDrawer} onOpenPlayground={onOpenPlayground} />
                <SpanDetailsWidgets />
                <SpanDetailsPanels />
              </SpanDetails>
            )}
          </Box>
        </Box>
      </Stack>

      <AddToDatasetDrawer traceId={traceId} open={addToDatasetOpen} onClose={() => setAddToDatasetOpen(false)} />
      {taskId && <CreateContinuousEvalDialog open={createEvalOpen} onClose={() => setCreateEvalOpen(false)} taskId={taskId} />}
    </BucketProvider>
  );
};
