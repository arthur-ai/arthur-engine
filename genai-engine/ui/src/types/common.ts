export type PaginationParams = {
  page: number;
  page_size: number;
};

export const DEFAULT_PAGINATION_PARAMS: PaginationParams = {
  page: 0,
  page_size: 25,
};
