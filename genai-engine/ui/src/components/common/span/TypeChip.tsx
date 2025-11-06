import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Chip } from "@mui/material";

type Props = {
  type: OpenInferenceSpanKind;
  active?: boolean;
};

export const TypeChip = ({ type, active = false }: Props) => {
  return (
    <Chip
      label={type}
      variant="outlined"
      size="small"
      color={TYPE_COLORS[type]}
      sx={(theme) => ({
        borderColor: TYPE_COLORS[type],
        color: TYPE_COLORS[type],
        fontSize: 10,
        maxHeight: 20,
        ...(active && {
          backgroundColor: theme.palette[TYPE_COLORS[type]]?.main ?? theme.palette.background.paper,
          color: theme.palette[TYPE_COLORS[type]]?.contrastText ?? theme.palette.text.primary,
        }),
      })}
    />
  );
};

/**
 * case OpenInferenceSpanKind.CHAIN:
      return "warning";
    case OpenInferenceSpanKind.LLM:
      return "primary";
    case OpenInferenceSpanKind.TOOL:
      return "success";
    case OpenInferenceSpanKind.RETRIEVER:
      return "info";
    case OpenInferenceSpanKind.AGENT:
      return "secondary";
    case OpenInferenceSpanKind.EMBEDDING:
      return "default";
    case OpenInferenceSpanKind.RERANKER:
      return "info";
    case OpenInferenceSpanKind.GUARDRAIL:
      return "error";
    case OpenInferenceSpanKind.EVALUATOR:
      return "default";
 */
const TYPE_COLORS = {
  [OpenInferenceSpanKind.CHAIN]: "warning",
  [OpenInferenceSpanKind.LLM]: "primary",
  [OpenInferenceSpanKind.TOOL]: "success",
  [OpenInferenceSpanKind.RETRIEVER]: "info",
  [OpenInferenceSpanKind.AGENT]: "secondary",
  [OpenInferenceSpanKind.EMBEDDING]: "info",
  [OpenInferenceSpanKind.RERANKER]: "info",
  [OpenInferenceSpanKind.GUARDRAIL]: "error",
  [OpenInferenceSpanKind.EVALUATOR]: "info",
} as const;
