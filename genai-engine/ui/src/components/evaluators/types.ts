import { LLMGetAllMetadataResponse, LLMEval } from "@/lib/api-client/api-client";

interface EvalRowExpansionProps {
  eval: LLMGetAllMetadataResponse;
  onExpandToFullScreen: () => void;
}

interface EvalsTableProps {
  evals: LLMGetAllMetadataResponse[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  expandedRows: Set<string>;
  onToggleRow: (evalName: string) => void;
  onExpandToFullScreen: (evalName: string) => void;
}

interface EvalVersionDrawerProps {
  open: boolean;
  onClose: () => void;
  taskId: string;
  evalName: string;
  selectedVersion: number | null;
  onSelectVersion: (version: number) => void;
}
interface EvalFullScreenViewProps {
  evalName: string;
  initialVersion?: number | null;
  onClose: () => void;
}

interface EvalDetailViewProps {
  eval: LLMEval | undefined;
  isLoading: boolean;
  error: Error | null;
  evalName: string;
  version: number | null;
  onClose?: () => void;
}

interface FiltersBase {
  page?: number;
  pageSize?: number;
  sort?: "asc" | "desc";
  created_after?: string | null;
  created_before?: string | null;
  model_provider?: string | null;
  model_name?: string | null;
}

interface EvalsFilters extends FiltersBase {
  llm_asset_names?: string[] | null;
}

interface EvalVersionsFilters extends FiltersBase {
  exclude_deleted?: boolean;
  min_version?: number | null;
  max_version?: number | null;
}

export type {
  EvalRowExpansionProps,
  EvalsTableProps,
  EvalVersionDrawerProps,
  EvalFullScreenViewProps,
  EvalDetailViewProps,
  EvalsFilters,
  EvalVersionsFilters,
};
