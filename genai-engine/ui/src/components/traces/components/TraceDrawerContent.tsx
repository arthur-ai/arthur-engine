import RefreshIcon from "@mui/icons-material/Refresh";
import { Button, ButtonGroup } from "@mui/material";
import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent, useMemo } from "react";

import { BucketProvider } from "../context/bucket-context";
import { useSelection } from "../hooks/useSelection";
import { buildThresholdsFromSample } from "../utils/duration";
import { flattenSpans, getSpanDuration } from "../utils/spans";

import { AddToDatasetDrawer } from "./add-to-dataset/Drawer";
import { DrawerPagination } from "./DrawerPagination";
import { SpanDetails, SpanDetailsHeader, SpanDetailsPanels, SpanDetailsWidgets } from "./SpanDetails";
import { SpanTree } from "./SpanTree";

import { CopyableChip } from "@/components/common";
import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";
import { computeTraceMetrics, getTrace } from "@/services/tracing";
import { wait } from "@/utils";

type Props = {
  id: string;
};

export const TraceDrawerContent = ({ id }: Props) => {
  const queryClient = useQueryClient();

  const api = useApi();
  const [selectedSpanId, select] = useSelection("span");

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

  const name = trace?.root_spans?.[0]?.span_name;

  // Flatten nested spans recursively
  const flatSpans = useMemo(() => flattenSpans(trace?.root_spans ?? []), [trace]);

  const rootSpan = trace?.root_spans?.[0];

  const onOpenDrawer = useEffectEvent(() => {
    if (!rootSpan) return;

    if (!selectedSpanId) {
      select(rootSpan.span_id);
    }

    if (flatSpans.findIndex((span) => span.span_id === selectedSpanId) === -1) {
      select(rootSpan.span_id);
    }
  });

  useEffect(onOpenDrawer, []);

  const thresholds = useMemo(() => buildThresholdsFromSample(flatSpans.map((span) => getSpanDuration(span) ?? 0)), [flatSpans]);

  if (!trace) return null;

  const selectedSpan = flatSpans.find((span) => span.span_id === selectedSpanId);

  return (
    <BucketProvider thresholds={thresholds}>
      <Stack spacing={0} sx={{ height: "100%" }}>
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

          <Stack gap={2} alignItems="flex-end">
            <ButtonGroup variant="outlined" size="small" disableElevation>
              <Button loading={refreshMetrics.isPending} onClick={() => refreshMetrics.mutate()} startIcon={<RefreshIcon />}>
                Refresh Metrics
              </Button>
              <AddToDatasetDrawer traceId={id} />
            </ButtonGroup>
          </Stack>
        </Stack>

        <Box sx={{ px: 4, py: 2, borderBottom: "1px solid", borderColor: "divider", backgroundColor: "grey.200" }}>
          <DrawerPagination />
        </Box>

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
            {rootSpan && <SpanTree spans={[rootSpan]} />}
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
