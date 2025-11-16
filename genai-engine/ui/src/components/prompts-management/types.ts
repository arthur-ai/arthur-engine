import { LLMGetAllMetadataResponse, AgenticPrompt, CreateAgenticPromptRequest } from "@/lib/api-client/api-client";

interface PromptRowExpansionProps {
  prompt: LLMGetAllMetadataResponse;
  onExpandToFullScreen: () => void;
}

interface PromptsTableProps {
  prompts: LLMGetAllMetadataResponse[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  expandedRows: Set<string>;
  onToggleRow: (promptName: string) => void;
  onExpandToFullScreen: (promptName: string) => void;
}

interface PromptVersionDrawerProps {
  open: boolean;
  onClose: () => void;
  taskId: string;
  promptName: string;
  selectedVersion: number | null;
  onSelectVersion: (version: number) => void;
}
interface PromptFullScreenViewProps {
  promptName: string;
  initialVersion?: number | null;
  onClose: () => void;
}

interface PromptDetailViewProps {
  promptData: AgenticPrompt | undefined;
  isLoading: boolean;
  error: Error | null;
  promptName: string;
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

interface PromptsFilters extends FiltersBase {
  llm_asset_names?: string[] | null;
}

interface PromptVersionsFilters extends FiltersBase {
  exclude_deleted?: boolean;
  min_version?: number | null;
  max_version?: number | null;
}

interface PromptsManagementHeaderProps {
  onCreatePrompt: () => void;
}

interface PromptFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (promptName: string, data: CreateAgenticPromptRequest) => Promise<void>;
  isLoading?: boolean;
}

export type {
  PromptRowExpansionProps,
  PromptsTableProps,
  PromptVersionDrawerProps,
  PromptFullScreenViewProps,
  PromptDetailViewProps,
  PromptsFilters,
  PromptVersionsFilters,
  PromptsManagementHeaderProps,
  PromptFormModalProps,
};
