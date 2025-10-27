import { useCallback, useState } from "react";

import { DEFAULT_PAGE_SIZE } from "@/constants/datasetConstants";

export const useDatasetsPaginationQuery = () => {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const handlePageChange = useCallback((_event: unknown, newPage: number) => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setPageSize(parseInt(event.target.value, 10));
      setPage(0);
    },
    []
  );

  const resetPage = useCallback(() => {
    setPage(0);
  }, []);

  return {
    page,
    pageSize,
    handlePageChange,
    handlePageSizeChange,
    resetPage,
  };
};
