import type { TraceTransform, TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";

// Re-export for convenience
export type { TraceTransform, TransformDefinition };

export interface TransformsTableProps {
  transforms: TraceTransform[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onView: (transform: TraceTransform) => void;
  onEdit: (transform: TraceTransform) => void;
  onDelete: (transformId: string) => void;
}

export interface TransformRowExpansionProps {
  transform: TraceTransform;
}

export interface TransformFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string, description: string, definition: TransformDefinition) => Promise<void>;
  isLoading: boolean;
  taskId: string | undefined;
  initialTransform?: TraceTransform;
}
