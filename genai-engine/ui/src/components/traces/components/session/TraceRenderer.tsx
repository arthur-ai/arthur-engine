import { TraceResponse } from "@/lib/api";
import { getMessages, getOutputMessages, tryFormatJson } from "@/utils/llm";
import { Box, Paper, Stack, Typography } from "@mui/material";
import { flattenSpans, getSpanInput, getSpanOutput } from "../../utils/spans";
import { Tabs } from "@/components/ui/Tabs";
import { Highlight } from "@/components/common/Highlight";
import { useTracesHistoryStore } from "../../stores/history.store";
import dayjs from "dayjs";
import { formatDate } from "@/utils/formatters";
import { TraceDrawerContent } from "../TraceDrawerContent";

type Props = {
  trace: TraceResponse;
};

export const TraceRenderer = ({ trace }: Props) => {
  const root = trace.root_spans?.[0];
  const push = useTracesHistoryStore((state) => state.push);

  if (!root) return null;

  function onOpenTraceDrawer() {
    push({
      type: "trace",
      id: trace.trace_id,
    });
  }

  const { children: _, ...rootSpan } = root;

  return (
    <Paper variant="outlined" className="grid grid-cols-2">
      <Tabs.Root defaultValue="formatted">
        <Tabs.List>
          <Tabs.Tab value="formatted">Formatted</Tabs.Tab>
          <Tabs.Tab value="raw">Raw</Tabs.Tab>

          <Tabs.Indicator />
        </Tabs.List>

        <Tabs.Panel value="formatted">
          <FormattedTrace trace={trace} />
        </Tabs.Panel>

        <Tabs.Panel value="raw" className="overflow-x-auto">
          <Highlight code={tryFormatJson(rootSpan)} language="json" />
        </Tabs.Panel>
      </Tabs.Root>

      <Box className="bg-gray-100 border-l p-2" sx={{ borderColor: "divider" }}>
        <Stack gap={1} alignItems="flex-start">
          <Stack
            component="button"
            color="primary.main"
            className="group cursor-pointer"
            onClick={onOpenTraceDrawer}
          >
            <Typography
              variant="body2"
              fontWeight={700}
              className="group-hover:underline"
            >
              Trace: {rootSpan.span_name} ({trace.trace_id})
            </Typography>
          </Stack>

          <Typography variant="body2" color="text.secondary">
            {formatDate(rootSpan.start_time)}
          </Typography>
        </Stack>
      </Box>
    </Paper>
  );
};

const FormattedTrace = ({ trace }: { trace: TraceResponse }) => {
  const root = trace.root_spans?.[0];
  if (!root) return null;

  const input = getSpanInput(root);
  const output = getSpanOutput(root);

  return (
    <Stack gap={1}>
      <MessageBubble label="Input" content={input} align="right" />
      <MessageBubble label="Output" content={output} align="left" />
    </Stack>
  );
};

const MessageBubble = ({
  label,
  content,
  align,
}: {
  label: string;
  content: string;
  align: "left" | "right";
}) => {
  return (
    <Stack
      component={Paper}
      variant="outlined"
      sx={{ p: 1, maxWidth: "75%" }}
      alignSelf={align === "left" ? "flex-start" : "flex-end"}
      gap={1}
    >
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Highlight code={tryFormatJson(content)} language="json" />
    </Stack>
  );
};
