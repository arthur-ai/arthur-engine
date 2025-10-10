import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";

import { useTracesStore } from "../store";
import { flattenSpans } from "../utils/spans";

import { SpanDetails } from "./SpanDetails";
import { SpanTree } from "./SpanTree";

import { CopyableChip } from "@/components/common";
import { useApi } from "@/hooks/useApi";
import { TaskResponse } from "@/lib/api";
import { getTrace } from "@/services/tracing";

type Props = {
  task: TaskResponse;
};

export const TraceDrawerContent = ({ task }: Props) => {
  const api = useApi();
  const [traceId] = useTracesStore((state) => state.context.selectedTraceId);
  const [selectedSpanId, store] = useTracesStore(
    (state) => state.context.selectedSpanId
  );

  const { data: trace } = useSuspenseQuery({
    queryKey: ["trace", traceId, { traceId, api, taskId: task?.id }],
    queryFn: () => getTrace(api!, { taskId: task!.id, traceId: traceId! }),
  });

  const name = trace?.root_spans?.[0]?.span_name;

  // Flatten nested spans recursively
  const flatSpans = useMemo(
    () => flattenSpans(trace?.root_spans ?? []),
    [trace]
  );

  const rootSpan = trace?.root_spans?.[0];

  useEffect(() => {
    if (rootSpan) {
      store.send({
        type: "selectSpan",
        id: rootSpan.span_id,
      });
    }
  }, [rootSpan, store]);

  if (!trace) return null;

  const selectedSpan = flatSpans?.find(
    (span) => span.span_id === selectedSpanId
  );

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
          label={traceId!}
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
        <Box sx={{ overflow: "auto", maxHeight: "100%" }}>
          {selectedSpan && <SpanDetails span={selectedSpan} />}
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
