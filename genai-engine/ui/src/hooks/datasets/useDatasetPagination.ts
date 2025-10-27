import { useCallback, useState } from "react";

import { DEFAULT_PAGE_SIZE } from "@/constants/datasetConstants";

export interface UseDatasetPaginationReturn {
  page: number;
  rowsPerPage: number;
  handlePageChange: (event: unknown, newPage: number) => void;
  handleRowsPerPageChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  resetPage: () => void;
}

export function useDatasetPagination(
  initialPageSize: number = DEFAULT_PAGE_SIZE
): UseDatasetPaginationReturn {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(initialPageSize);

  const handlePageChange = useCallback((_event: unknown, newPage: number) => {
    setPage(newPage);
  }, []);

  const handleRowsPerPageChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setRowsPerPage(parseInt(event.target.value, 10));
      setPage(0);
    },
    []
  );

  const resetPage = useCallback(() => {
    setPage(0);
  }, []);

  return {
    page,
    rowsPerPage,
    handlePageChange,
    handleRowsPerPageChange,
    resetPage,
  };
}
