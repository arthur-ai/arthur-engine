import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent, useMemo } from "react";

import { useTracesStore } from "../store";
import { flattenSpans } from "../utils/spans";

import {
  SpanDetails,
  SpanDetailsHeader,
  SpanDetailsPanels,
  SpanDetailsWidgets,
} from "./SpanDetails";
import { SpanTree } from "./SpanTree";

import { CopyableChip } from "@/components/common";
import { useApi } from "@/hooks/useApi";
import { getTrace } from "@/services/tracing";

type Props = {
  id: string;
};

export const TraceDrawerContent = ({ id }: Props) => {
  const api = useApi();
  const [selected, store] = useTracesStore((state) => state.context.selected);

  const { span: spanId } = selected;

  const { data: trace } = useSuspenseQuery({
    queryKey: ["trace", id, { id, api }],
    queryFn: () => getTrace(api!, { traceId: id! }),
  });

  const name = trace?.root_spans?.[0]?.span_name;

  // Flatten nested spans recursively
  const flatSpans = useMemo(
    () => flattenSpans(trace?.root_spans ?? []),
    [trace]
  );

  const rootSpan = trace?.root_spans?.[0];

  const onOpenDrawer = useEffectEvent(() => {
    if (selected.span) return;
    if (!rootSpan) return;

    store.send({
      type: "selectSpan",
      id: rootSpan.span_id,
    });
  });

  useEffect(() => {
    onOpenDrawer();
  }, []);

  if (!trace) return null;

  const selectedSpan = flatSpans?.find((span) => span.span_id === spanId);

  return (
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
        <Stack direction="column" spacing={0}>
          <Typography variant="body2" color="text.secondary">
            Trace Details
          </Typography>
          <Typography variant="h5" color="text.primary" fontWeight="bold">
            {name}
          </Typography>
        </Stack>

        <CopyableChip
          label={id!}
          sx={{ fontFamily: "monospace", maxWidth: 200 }}
        />
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

        <Skeleton
          variant="rounded"
          width={200}
          height={32}
          sx={{ borderRadius: 16 }}
        />
      </Stack>

      <Box sx={{ flexGrow: 1, p: 4 }}>
        <Skeleton
          variant="rectangular"
          height="100%"
          sx={{ borderRadius: 1 }}
        />
      </Box>
    </Stack>
  );
};
