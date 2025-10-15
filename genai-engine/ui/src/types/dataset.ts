export interface Dataset {
  id: string;
  name: string;
  rowCount: number;
  columnCount: number;
  versionTag: string;
  lastModified: string;
  owner: string;
  taskId: string;
  createdAt: string;
  description?: string;
  currentVersion?: number;
}

export interface DatasetVersion {
  id: string;
  versionNumber: number;
  createdAt: string;
  createdBy: string;
  rowCount: number;
  columnCount: number;
  changes?: string;
  isCurrent: boolean;
}

export interface DatasetFormData {
  name: string;
  description?: string;
}

export type SortField = "name" | "lastModified" | "rowCount" | "createdAt";
export type SortOrder = "asc" | "desc";

export interface DatasetFilters {
  searchQuery?: string;
  sortBy: SortField;
  sortOrder: SortOrder;
  page: number;
  pageSize: number;
}

export interface PaginatedDatasets {
  datasets: Dataset[];
  total: number;
  page: number;
  pageSize: number;
}
