export type SortOrder = "asc" | "desc";

export interface DatasetFilters {
  searchQuery?: string;
  sortOrder: SortOrder;
  page: number;
  pageSize: number;
}
