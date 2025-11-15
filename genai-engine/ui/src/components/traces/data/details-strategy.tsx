import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Box, Paper } from "@mui/material";
import Typography from "@mui/material/Typography";

import { LLMMetricsPanel } from "../components/LLMMetricsPanel";
import { getSpanInput, getSpanInputMimeType, getSpanModel, getSpanOutput } from "../utils/spans";

import { TokenCostTooltip, TokenCountTooltip } from "./common";

import { Highlight } from "@/components/common/Highlight";
import { MessageRenderer } from "@/components/common/llm/MessageRenderer";
import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { getCost, getMessages, getOutputMessages, getTokens, tryFormatJson } from "@/utils/llm";

function getHighlightType(span: NestedSpanWithMetricsResponse) {
  const mime = getSpanInputMimeType(span);
  let type = "none";

  if (mime === "application/json") {
    type = "json";
  }

  return { mime, type };
}

const PANELS = {
  INPUT: {
    label: "Input",
    render: (span: NestedSpanWithMetricsResponse) => {
      const { type } = getHighlightType(span);
      return <Highlight code={tryFormatJson(getSpanInput(span))} language={type} />;
    },
    defaultOpen: true,
  },
  OUTPUT: {
    label: "Output",
    render: (span: NestedSpanWithMetricsResponse) => {
      const { type } = getHighlightType(span);
      return <Highlight code={tryFormatJson(getSpanOutput(span))} language={type} />;
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
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    widgets: [],
  },
  {
    kind: OpenInferenceSpanKind.CHAIN,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    widgets: [],
  },
  {
    kind: OpenInferenceSpanKind.LLM,
    panels: [
      {
        label: "Input Messages",
        render: (span: NestedSpanWithMetricsResponse) => {
          const messages = getMessages(span);

          return (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {messages.map(({ message }, index) => (
                <MessageRenderer message={message} key={index} />
              ))}
            </Box>
          );
        },
        defaultOpen: true,
      },
      {
        label: "Output Messages",
        render: (span: NestedSpanWithMetricsResponse) => {
          const messages = getOutputMessages(span);

          return (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {messages.map((message, index) => (
                <MessageRenderer message={message.message} key={index} />
              ))}
            </Box>
          );
        },
        defaultOpen: true,
      },
      PANELS.METRICS,
    ],
    raw: PANELS.RAW_DATA,
    widgets: [
      {
        render: (span: NestedSpanWithMetricsResponse) => {
          const model = getSpanModel(span);

          return <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12}>{`model: ${model}`}</Typography>;
        },
      },
      {
        render: (span: NestedSpanWithMetricsResponse) => {
          const cost = getCost(span);

          const na = (
            <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12}>
              Cost: N/A
            </Typography>
          );

          if (!cost) return na;

          const { prompt, completion, total } = cost;

          if (!total) return na;

          return <TokenCostTooltip prompt={prompt} completion={completion} total={total} />;
        },
      },
      {
        render: (span: NestedSpanWithMetricsResponse) => {
          const tokens = getTokens(span);

          const na = (
            <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12}>
              Tokens: N/A
            </Typography>
          );

          if (!tokens) return na;

          const { input, output, total } = tokens;

          if (!total) return na;

          return <TokenCountTooltip prompt={input} completion={output} total={total} />;
        },
      },
    ],
  },
  {
    kind: OpenInferenceSpanKind.TOOL,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    widgets: [],
  },
  {
    kind: OpenInferenceSpanKind.RETRIEVER,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    widgets: [],
  },
] as const;

export function getSpanDetailsStrategy(kind: OpenInferenceSpanKind) {
  const strategy = spanDetailsStrategy.find((strategy) => strategy.kind === kind);

  return strategy;
}

export type SpanDetailsStrategy = ReturnType<typeof getSpanDetailsStrategy>;
