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
