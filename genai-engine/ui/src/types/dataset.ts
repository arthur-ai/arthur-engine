export interface Dataset {
  id: string;
  name: string;
  description?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at: number;
  updated_at: number;
}

export interface DatasetFormData {
  name: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export type SortOrder = "asc" | "desc";

export interface DatasetFilters {
  searchQuery?: string;
  sortOrder: SortOrder;
  page: number;
  pageSize: number;
}
