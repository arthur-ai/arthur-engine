import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";

export interface DatasetTransform {
  id: string;
  dataset_id: string;
  name: string;
  description?: string | null;
  definition: TransformDefinition;
  created_at: number;
  updated_at: number;
}

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
