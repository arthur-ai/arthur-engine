import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import SearchIcon from "@mui/icons-material/Search";
import SquareFootIcon from "@mui/icons-material/SquareFoot";

export const SPAN_TYPE_ICONS = {
  [OpenInferenceSpanKind.LLM]: <AutoAwesomeIcon />,
  [OpenInferenceSpanKind.RETRIEVER]: <SearchIcon />,
  [OpenInferenceSpanKind.EMBEDDING]: <AutoAwesomeIcon />,
  [OpenInferenceSpanKind.CHAIN]: <AutoAwesomeIcon />,
  [OpenInferenceSpanKind.AGENT]: <AutoAwesomeIcon />,
  [OpenInferenceSpanKind.TOOL]: <SquareFootIcon />,
  [OpenInferenceSpanKind.RERANKER]: <AutoAwesomeIcon />,
  [OpenInferenceSpanKind.GUARDRAIL]: <AutoAwesomeIcon />,
  [OpenInferenceSpanKind.EVALUATOR]: <AutoAwesomeIcon />,
};

export const TIME_RANGES = {
  "5 minutes": "5 minutes",
  "30 minutes": "30 minutes",
  "1 day": "1 day",
  "1 week": "1 week",
  "1 month": "1 month",
  "3 months": "3 months",
  "1 year": "1 year",
  "all time": "all time",
} as const;
export type TimeRange = (typeof TIME_RANGES)[keyof typeof TIME_RANGES];

export const LEVELS = ["trace", "span", "session", "user"] as const;
export type Level = (typeof LEVELS)[number];
