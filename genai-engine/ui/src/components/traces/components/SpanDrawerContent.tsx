import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import RefreshIcon from "@mui/icons-material/Refresh";
import { Box, Button, ButtonGroup, Stack, Typography } from "@mui/material";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";

import { useTracesHistoryStore } from "../stores/history.store";
import { useSelectionStore } from "../stores/selection.store";
import { isSpanOfType } from "../utils/spans";

import { DrawerPagination } from "./DrawerPagination";
import { SpanDetails, SpanDetailsPanels, SpanDetailsWidgets } from "./SpanDetails";

import { CopyableChip } from "@/components/common";
import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";
import { computeSpanMetrics, getSpan } from "@/services/tracing";
import { wait } from "@/utils";

type Props = {
  id: string;
};

export const SpanDrawerContent = ({ id }: Props) => {
  const api = useApi();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const push = useTracesHistoryStore((state) => state.push);
  const select = useSelectionStore((state) => state.select);

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
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.spans.byId(id), data);
    },
  });

  const isLLM = isSpanOfType(span, OpenInferenceSpanKind.LLM);

  const onOpenTraceDrawer = () => {
    select("span", span.span_id);
    push({
      type: "trace",
      id: span.trace_id,
    });
  };

  const handleOpenInPlayground = () => {
    if (span.task_id) {
      navigate(`/tasks/${span.task_id}/playgrounds/prompts?spanId=${span.span_id}`);
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
          backgroundColor: "grey.100",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="column" spacing={0}>
          <Typography variant="body2" color="text.secondary">
            Span Details
          </Typography>
          <Stack direction="row" gap={2}>
            <Typography variant="h6" color="text.primary" fontWeight={700}>
              {span.span_name}
            </Typography>
            <CopyableChip
              label={id!}
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
                <Button loading={refreshMetrics.isPending} onClick={() => refreshMetrics.mutate()} startIcon={<RefreshIcon />}>
                  Refresh Metrics
                </Button>
              </ButtonGroup>
            )}
          </Stack>
        </Stack>
      </Stack>

      <Box sx={{ px: 4, py: 2, borderBottom: "1px solid", borderColor: "divider", backgroundColor: "grey.200" }}>
        <DrawerPagination />
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
