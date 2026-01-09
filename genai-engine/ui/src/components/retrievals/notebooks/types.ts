import type { RagNotebookSummary } from "@/lib/api-client/api-client";

export interface RagNotebooksHeaderProps {
  onCreateNotebook: () => void;
}

export interface RagNotebooksTableProps {
  notebooks: RagNotebookSummary[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onRowClick: (notebookId: string) => void;
  onLaunchNotebook: (notebookId: string) => void;
  onDelete: (notebookId: string) => Promise<void>;
}
