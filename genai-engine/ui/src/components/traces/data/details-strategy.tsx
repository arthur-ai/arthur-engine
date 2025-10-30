import {
  OpenInferenceSpanKind,
  SemanticConventions,
} from "@arizeai/openinference-semantic-conventions";
import { Box, Paper } from "@mui/material";
import Typography from "@mui/material/Typography";

import { getSpanCost, getSpanModel } from "../utils/spans";

import { Highlight } from "@/components/common/Highlight";
import { MessageRenderer } from "@/components/common/llm/MessageRenderer";
import { OutputMessageRenderer } from "@/components/common/llm/OutputMessageRenderer";
import { NestedSpanWithMetricsResponse } from "@/lib/api";
import {
  getInputTokens,
  getMessages,
  getOutputMessages,
  getOutputTokens,
  getTotalTokens,
  isLLMOutputMessage,
  tryFormatJson,
} from "@/utils/llm";
import { LLMMetricsPanel } from "../components/LLMMetricsPanel";
import { TokenCountWidget } from "../components/widgets/TokenCount";

function getHighlightType(span: NestedSpanWithMetricsResponse) {
  const mime: string =
    span.raw_data.attributes[SemanticConventions.INPUT_MIME_TYPE] ?? undefined;
  let type = "none";

  if (mime?.startsWith("application/json")) {
    type = "json";
  }

  return { mime, type };
}

const PANELS = {
  INPUT: {
    label: "Input",
    render: (span: NestedSpanWithMetricsResponse) => {
      const { type } = getHighlightType(span);
      return (
        <Highlight
          code={tryFormatJson(
            span.raw_data.attributes[SemanticConventions.INPUT_VALUE]
          )}
          language={type}
        />
      );
    },
    defaultOpen: true,
  },
  OUTPUT: {
    label: "Output",
    render: (span: NestedSpanWithMetricsResponse) => {
      const { type } = getHighlightType(span);
      return (
        <Highlight
          code={tryFormatJson(
            span.raw_data.attributes[SemanticConventions.OUTPUT_VALUE]
          )}
          language={type}
        />
      );
    },
    defaultOpen: true,
  },
  RAW_DATA: {
    label: "Raw Data",
    render: (span: NestedSpanWithMetricsResponse) => {
      return <Highlight code={tryFormatJson(span.raw_data)} language="json" />;
    },
    defaultOpen: false,
  },
  METRICS: {
    label: "Metrics",
    render: (span: NestedSpanWithMetricsResponse) => {
      return <LLMMetricsPanel span={span} />;
    },
    defaultOpen: true,
  },
} as const;

const spanDetailsStrategy = [
  {
    kind: OpenInferenceSpanKind.AGENT,
    panels: [PANELS.INPUT, PANELS.OUTPUT, PANELS.RAW_DATA],
    widgets: [],
  },
  {
    kind: OpenInferenceSpanKind.CHAIN,
    panels: [PANELS.INPUT, PANELS.OUTPUT, PANELS.RAW_DATA],
    widgets: [],
  },
  {
    kind: OpenInferenceSpanKind.LLM,
    panels: [
      {
        label: "Input Messages",
        render: (span: NestedSpanWithMetricsResponse) => {
          const messages = getMessages(span);
          const model = getSpanModel(span);

          return (
            <Paper
              variant="outlined"
              sx={{ display: "flex", flexDirection: "column" }}
            >
              <Box
                p={1}
                sx={{ borderBottom: "1px solid", borderColor: "divider" }}
              >
                <Typography
                  variant="body2"
                  color="text.primary"
                  fontWeight={700}
                  fontSize={12}
                >
                  {model}
                </Typography>
              </Box>
              <Box
                p={1}
                sx={{ display: "flex", flexDirection: "column", gap: 1 }}
              >
                {messages.map((message, index) => (
                  <MessageRenderer message={message} key={index} />
                ))}
              </Box>
            </Paper>
          );
        },
        defaultOpen: true,
      },
      {
        label: "Output Messages",
        render: (span: NestedSpanWithMetricsResponse) => {
          const messages = getOutputMessages(span);
          const model = getSpanModel(span);

          return (
            <Paper
              variant="outlined"
              sx={{
                display: "flex",
                flexDirection: "column",
                fontSize: "12px",
              }}
            >
              <Box
                p={1}
                sx={{ borderBottom: "1px solid", borderColor: "divider" }}
              >
                <Typography
                  variant="body2"
                  color="text.primary"
                  fontWeight={700}
                  fontSize={12}
                >
                  {model}
                </Typography>
              </Box>
              <Box
                p={1}
                sx={{ display: "flex", flexDirection: "column", gap: 1 }}
              >
                {messages.map((message, index) =>
                  isLLMOutputMessage(message) ? (
                    <OutputMessageRenderer message={message} key={index} />
                  ) : (
                    <MessageRenderer message={message} key={index} />
                  )
                )}
              </Box>
            </Paper>
          );
        },
        defaultOpen: true,
      },
      PANELS.METRICS,
      PANELS.RAW_DATA,
    ],
    widgets: [
      {
        render: (span: NestedSpanWithMetricsResponse) => {
          const model = getSpanModel(span);

          return (
            <Typography variant="body2" color="text.secondary">
              model: {model}
            </Typography>
          );
        },
      },
      {
        render: (span: NestedSpanWithMetricsResponse) => {
          const cost = getSpanCost(span);

          return (
            <Typography variant="body2" color="text.secondary">
              cost: ${cost.toFixed(5)}
            </Typography>
          );
        },
      },
      {
        render: (span: NestedSpanWithMetricsResponse) => {
          return (
            <TokenCountWidget
              input={getInputTokens(span)}
              output={getOutputTokens(span)}
              total={getTotalTokens(span)}
            />
          );
        },
      },
    ],
  },
  {
    kind: OpenInferenceSpanKind.TOOL,
    panels: [PANELS.INPUT, PANELS.OUTPUT, PANELS.RAW_DATA],
    widgets: [],
  },
  {
    kind: OpenInferenceSpanKind.RETRIEVER,
    panels: [PANELS.INPUT, PANELS.OUTPUT, PANELS.RAW_DATA],
    widgets: [],
  },
] as const;

export function getSpanDetailsStrategy(kind: OpenInferenceSpanKind) {
  const strategy = spanDetailsStrategy.find(
    (strategy) => strategy.kind === kind
  );

  return strategy;
}

export type SpanDetailsStrategy = ReturnType<typeof getSpanDetailsStrategy>;
