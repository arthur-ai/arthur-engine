import { PaginationState } from "@tanstack/react-table";
import { useMemo, useState } from "react";

export const useMRTPagination = ({ initialPageSize = 25, initialPageIndex = 0 }: { initialPageSize?: number; initialPageIndex?: number } = {}) => {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: initialPageIndex ?? 0,
    pageSize: initialPageSize ?? 25,
  });

  return useMemo(
    () => ({
      pagination,
      props: {
        manualPagination: true,
        onPaginationChange: setPagination,
      },
    }),
    [pagination, setPagination]
  );
};
