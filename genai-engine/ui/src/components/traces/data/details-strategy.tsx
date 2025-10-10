import {
  OpenInferenceSpanKind,
  SemanticConventions,
} from "@arizeai/openinference-semantic-conventions";
import Typography from "@mui/material/Typography";

import { getSpanCost, getSpanModel } from "../utils/spans";

import { Highlight } from "@/components/common/Highlight";
import { NestedSpanWithMetricsResponse } from "@/lib/api";

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
          code={span.raw_data.attributes[SemanticConventions.INPUT_VALUE]}
          language={type}
        />
      );
    },
  },
  OUTPUT: {
    label: "Output",
    render: (span: NestedSpanWithMetricsResponse) => {
      const { type } = getHighlightType(span);
      return (
        <Highlight
          code={span.raw_data.attributes[SemanticConventions.OUTPUT_VALUE]}
          language={type}
        />
      );
    },
  },
  RAW_DATA: {
    label: "Raw Data",
    render: (span: NestedSpanWithMetricsResponse) => {
      return (
        <Highlight
          code={JSON.stringify(span.raw_data, null, 2)}
          language="json"
        />
      );
    },
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
    panels: [PANELS.RAW_DATA],
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
    ],
  },
  {
    kind: OpenInferenceSpanKind.TOOL,
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
