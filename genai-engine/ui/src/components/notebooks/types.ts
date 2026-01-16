import { NotebookSummary } from "@/lib/api-client/api-client";

export interface NotebooksHeaderProps {
  onCreateNotebook: () => void;
}

export interface NotebooksTableProps {
  notebooks: NotebookSummary[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onRowClick: (notebookId: string) => void;
  onLaunchNotebook: (notebookId: string) => void;
  onDelete: (notebookId: string) => Promise<void>;
}
