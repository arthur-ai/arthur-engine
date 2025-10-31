import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import RefreshIcon from "@mui/icons-material/Refresh";
import { Box, Button, Stack, Typography } from "@mui/material";
import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query";

import { useTracesHistoryStore } from "../stores/history.store";
import { isSpanOfType } from "../utils/spans";

import {
  SpanDetails,
  SpanDetailsPanels,
  SpanDetailsWidgets,
} from "./SpanDetails";

import { CopyableChip } from "@/components/common";
import { LoadingButton } from "@/components/ui/LoadingButton";
import { useApi } from "@/hooks/useApi";
import { computeSpanMetrics, getSpan } from "@/services/tracing";
import { wait } from "@/utils";
import { queryKeys } from "@/lib/queryKeys";

type Props = {
  id: string;
};

export const SpanDrawerContent = ({ id }: Props) => {
  const api = useApi();
  const queryClient = useQueryClient();

  const push = useTracesHistoryStore((state) => state.push);

  const { data: span } = useSuspenseQuery({
    queryKey: queryKeys.spans.byId(id),
    queryFn: () => getSpan(api!, { spanId: id! }),
  });

  const refreshMetrics = useMutation({
    mutationFn: async () => {
      const [, data] = await Promise.all([
        wait(1000),
        computeSpanMetrics(api!, { spanId: id! }),
      ]);

      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.spans.byId(id), data);
    },
  });

  const isLLM = isSpanOfType(span, OpenInferenceSpanKind.LLM);

  const onOpenTraceDrawer = () => {
    push({
      type: "trace",
      id: span.trace_id,
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
          <Stack direction="row" spacing={0} sx={{ marginLeft: "auto" }}>
            <CopyableChip
              label={id!}
              sx={{
                fontFamily: "monospace",
                ...(isLLM && {
                  borderTopRightRadius: 0,
                  borderBottomRightRadius: 0,
                }),
              }}
            />
            {isLLM && (
              <LoadingButton
                className="px-4 rounded-r-full text-nowrap shrink-0"
                loading={refreshMetrics.isPending}
                onClick={() => refreshMetrics.mutate()}
              >
                <span className="flex items-center gap-1">
                  <RefreshIcon
                    sx={{
                      fontSize: 16,
                      width: 16,
                      height: "1lh",
                      flexShrink: 0,
                    }}
                  />
                  <Typography variant="caption" lineHeight={1}>
                    Refresh Metrics
                  </Typography>
                </span>
              </LoadingButton>
            )}
          </Stack>
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
