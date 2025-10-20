import { Box, Button, Stack, Typography } from "@mui/material";
import { useSuspenseQuery } from "@tanstack/react-query";

import { useTracesStore } from "../store";

import {
  SpanDetails,
  SpanDetailsPanels,
  SpanDetailsWidgets,
} from "./SpanDetails";

import { CopyableChip } from "@/components/common";
import { useApi } from "@/hooks/useApi";
import { getSpan } from "@/services/tracing";

type Props = {
  id: string;
};

export const SpanDrawerContent = ({ id }: Props) => {
  const api = useApi();
  const [, store] = useTracesStore(() => null);

  const { data: span } = useSuspenseQuery({
    queryKey: ["span", id, { id, api }],
    queryFn: () => getSpan(api!, { spanId: id! }),
  });

  const onOpenTraceDrawer = () => {
    store.send({
      type: "openDrawer",
      for: "trace",
      id: span.trace_id,
    });
    store.send({
      type: "selectSpan",
      id: id,
    });
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
          backgroundColor: "grey.100",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="column" spacing={0}>
          <Typography variant="body2" color="text.secondary">
            Span Details
          </Typography>
          <Typography variant="h6" color="text.primary" fontWeight={700}>
            {span.span_name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Part of trace{" "}
            <Button
              variant="text"
              size="small"
              color="primary"
              sx={{ fontFamily: "monospace" }}
              onClick={onOpenTraceDrawer}
            >
              {span.trace_id}
            </Button>
          </Typography>
        </Stack>

        <Stack direction="column" spacing={1} alignItems="flex-end">
          <CopyableChip label={span.span_id} sx={{ fontFamily: "monospace" }} />
        </Stack>
      </Stack>
      <Box sx={{ overflow: "auto", maxHeight: "100%", px: 4, py: 2 }}>
        <SpanDetails span={span}>
          <SpanDetailsWidgets />
          <SpanDetailsPanels />
        </SpanDetails>
      </Box>
    </Stack>
  );
};
