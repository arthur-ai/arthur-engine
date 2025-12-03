import type { DatasetTransform, TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";

// Re-export for convenience
export type { DatasetTransform, TransformDefinition };

export interface TransformsTableProps {
  transforms: DatasetTransform[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onView: (transform: DatasetTransform) => void;
  onEdit: (transform: DatasetTransform) => void;
  onDelete: (transformId: string) => void;
}

export interface TransformRowExpansionProps {
  transform: DatasetTransform;
}

export interface TransformFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string, description: string, definition: TransformDefinition) => Promise<void>;
  isLoading: boolean;
  datasetId: string | undefined;
  initialTransform?: DatasetTransform;
}
