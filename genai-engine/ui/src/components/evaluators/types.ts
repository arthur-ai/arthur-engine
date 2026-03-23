import { LLMGetAllMetadataResponse, LLMEval, CreateEvalRequest } from "@/lib/api-client/api-client";

interface EvalsTableProps {
  evals: LLMGetAllMetadataResponse[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onExpandToFullScreen: (evalName: string) => void;
  onDelete?: (evalName: string) => Promise<void>;
}

interface EvalVersionDrawerProps {
  open: boolean;
  onClose: () => void;
  taskId: string;
  evalName: string;
  selectedVersion: number | null;
  latestVersion: number | null;
  onSelectVersion: (version: number) => void;
  onDelete?: (version: number) => Promise<void>;
  onRefetchTrigger?: number;
}
interface EvalFullScreenViewProps {
  evalName: string;
  initialVersion?: number | null;
  onClose: () => void;
}

interface EvalDetailViewProps {
  evalData: LLMEval | undefined;
  isLoading: boolean;
  error: Error | null;
  evalName: string;
  version: number | null;
  latestVersion: number | null;
  taskId: string;
  onClose?: () => void;
  onRefetch?: (newVersion?: number) => void;
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

interface EvaluatorsHeaderProps {
  onCreateEval: () => void;
}

interface EvalFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (evalName: string, data: CreateEvalRequest) => Promise<void>;
  isLoading?: boolean;
}

export type {
  EvalsTableProps,
  EvalVersionDrawerProps,
  EvalFullScreenViewProps,
  EvalDetailViewProps,
  EvalsFilters,
  EvalVersionsFilters,
  EvaluatorsHeaderProps,
  EvalFormModalProps,
};
