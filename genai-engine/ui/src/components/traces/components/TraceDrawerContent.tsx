import { Menu } from "@base-ui-components/react/menu";
import AddIcon from "@mui/icons-material/Add";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import RefreshIcon from "@mui/icons-material/Refresh";
import TroubleshootIcon from "@mui/icons-material/Troubleshoot";
import { Button, List, ListItemButton, ListItemText, Paper } from "@mui/material";
import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { BucketProvider } from "../context/bucket-context";
import { useSelection } from "../hooks/useSelection";
import { buildThresholdsFromSample } from "../utils/duration";
import { flattenSpans, getSpanDuration } from "../utils/spans";

import { AddToDatasetDrawer } from "./add-to-dataset/Drawer";
import { DrawerPagination } from "./DrawerPagination";
import { FeedbackPanel } from "./feedback/FeedbackPanel";
import { SpanDetails, SpanDetailsHeader, SpanDetailsPanels, SpanDetailsWidgets } from "./SpanDetails";
import { SpanTree } from "./SpanTree";

import { CopyableChip } from "@/components/common";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";
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
  const [addToDatasetOpen, setAddToDatasetOpen] = useState(false);

  const containerRef = useRef<HTMLDivElement | null>(null);

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
    onSuccess: (data) => {
      queryClient.setQueryData(["trace", id], data);
    },
  });

  const name =
    trace?.root_spans?.length === 1
      ? trace.root_spans[0].span_name
      : trace?.root_spans && trace.root_spans.length > 1
        ? `${trace.root_spans[0].span_name} (+${trace.root_spans.length - 1} more root${trace.root_spans.length > 2 ? "s" : ""})`
        : undefined;

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

  useEffect(onOpenDrawer, []);

  const thresholds = useMemo(() => buildThresholdsFromSample(flatSpans.map((span) => getSpanDuration(span) ?? 0)), [flatSpans]);

  if (!trace) return null;

  const selectedSpan = flatSpans.find((span) => span.span_id === selectedSpanId);

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
            backgroundColor: "grey.100",
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
                label={id!}
                sx={{
                  fontFamily: "monospace",
                }}
              />
            </Stack>
          </Stack>

          <Stack gap={1} alignItems="center" direction="row">
            <Menu.Root>
              <Menu.Trigger render={<Button variant="contained" size="small" endIcon={<ArrowDropDownIcon />} loading={refreshMetrics.isPending} />}>
                Trace Actions
              </Menu.Trigger>
              <Menu.Portal keepMounted container={containerRef.current}>
                <Menu.Positioner sideOffset={8} side="bottom" align="center">
                  <Menu.Popup render={<List component={Paper} dense className="outline-none origin-(--transform-origin)" />}>
                    <Menu.Item render={<ListItemButton onClick={() => refreshMetrics.mutate()} />}>
                      <RefreshIcon sx={{ mr: 1, fontSize: 16 }} />
                      <ListItemText primary="Refresh Metrics" />
                    </Menu.Item>
                    <Menu.Item render={<ListItemButton onClick={() => setAddToDatasetOpen(true)} />}>
                      <AddIcon sx={{ mr: 1, fontSize: 16 }} />
                      <ListItemText primary="Add to Dataset" secondary="Add this trace to a dataset" />
                    </Menu.Item>
                    <Menu.Separator />
                    <Menu.Item render={<ListItemButton to={`/tasks/${task!.id}/live-evals/new?traceId=${id}`} component={Link} />}>
                      <TroubleshootIcon sx={{ mr: 1, fontSize: 16 }} />
                      <ListItemText primary="Evaluate Traces Like This" secondary="Evaluate traces that are similar to this one" />
                    </Menu.Item>
                  </Menu.Popup>
                </Menu.Positioner>
              </Menu.Portal>
            </Menu.Root>
          </Stack>
        </Stack>

        <Stack
          direction="row"
          alignItems="center"
          sx={{ px: 4, py: 2, borderBottom: "1px solid", borderColor: "divider", backgroundColor: "grey.200" }}
        >
          <DrawerPagination />
          <Box sx={{ flex: 1 }} />
          <FeedbackPanel containerRef={containerRef} annotation={trace.annotation} traceId={id} />
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
              backgroundColor: "grey.100",
              overflow: "auto",
              maxHeight: "100%",
            }}
          >
            {trace?.root_spans && <SpanTree spans={trace.root_spans} />}
          </Box>
          <Box sx={{ overflow: "auto", maxHeight: "100%", p: 2 }}>
            {selectedSpan && (
              <SpanDetails span={selectedSpan}>
                <SpanDetailsHeader />
                <SpanDetailsWidgets />
                <SpanDetailsPanels />
              </SpanDetails>
            )}
          </Box>
        </Box>
      </Stack>

      <AddToDatasetDrawer traceId={id} open={addToDatasetOpen} onClose={() => setAddToDatasetOpen(false)} />
    </BucketProvider>
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
          backgroundColor: "grey.100",
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
