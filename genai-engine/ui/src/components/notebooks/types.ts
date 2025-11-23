export interface NotebooksHeaderProps {
  onCreateNotebook: () => void;
}

export interface NotebooksTableProps {
  notebooks: any[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onRowClick: (notebookId: string) => void;
  onLaunchNotebook: (notebookId: string) => void;
  onDelete: (notebookId: string) => Promise<void>;
}

