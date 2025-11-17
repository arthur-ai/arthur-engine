import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Box } from "@mui/material";
import Typography from "@mui/material/Typography";

import { ToolsTab } from "../components/llm/ToolsTab";
import { LLMMetricsPanel } from "../components/LLMMetricsPanel";
import { getSpanDuration, getSpanInput, getSpanInputMimeType, getSpanModel, getSpanOutput } from "../utils/spans";

import { DurationCell, TokenCostTooltip, TokenCountTooltip } from "./common";

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
  TOOLS: {
    label: "Tools",
    render: (span: NestedSpanWithMetricsResponse) => <ToolsTab span={span} />,
    defaultOpen: false,
  },
} as const;

const WIDGETS = {
  LATENCY: {
    wrapped: false,
    render: (span: NestedSpanWithMetricsResponse) => {
      const latency = getSpanDuration(span);

      if (typeof latency !== "number") return null;

      return <DurationCell duration={latency} />;
    },
  },
} as const;

const spanDetailsStrategy = [
  {
    kind: OpenInferenceSpanKind.AGENT,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
  {
    kind: OpenInferenceSpanKind.CHAIN,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
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
    tabs: [PANELS.TOOLS, PANELS.RAW_DATA],
    widgets: [
      {
        wrapped: true,
        render: (span: NestedSpanWithMetricsResponse) => {
          const model = getSpanModel(span);

          return <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12}>{`model: ${model}`}</Typography>;
        },
      },
      {
        wrapped: true,
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
        wrapped: true,
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
      WIDGETS.LATENCY,
    ],
  },
  {
    kind: OpenInferenceSpanKind.TOOL,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
  {
    kind: OpenInferenceSpanKind.RETRIEVER,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
  {
    kind: OpenInferenceSpanKind.RERANKER,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
  {
    kind: OpenInferenceSpanKind.GUARDRAIL,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
  {
    kind: OpenInferenceSpanKind.EVALUATOR,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
  {
    kind: OpenInferenceSpanKind.EMBEDDING,
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
  {
    kind: "UNKNOWN",
    panels: [PANELS.INPUT, PANELS.OUTPUT],
    raw: PANELS.RAW_DATA,
    tabs: [PANELS.RAW_DATA],
    widgets: [WIDGETS.LATENCY],
  },
] as const;

export function getSpanDetailsStrategy(kind: OpenInferenceSpanKind) {
  const strategy = spanDetailsStrategy.find((strategy) => strategy.kind === kind);

  return strategy;
}

export type SpanDetailsStrategy = ReturnType<typeof getSpanDetailsStrategy>;
