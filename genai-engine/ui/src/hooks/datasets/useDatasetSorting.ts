import { useCallback, useMemo, useState } from "react";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { sortRows } from "@/utils/datasetSortUtils";

export interface UseDatasetSortingReturn {
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  sortedRows: DatasetVersionRowResponse[];
  handleSort: (column: string) => void;
}

export function useDatasetSorting(
  rows: DatasetVersionRowResponse[]
): UseDatasetSortingReturn {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    return sortRows(rows, sortColumn, sortDirection);
  }, [rows, sortColumn, sortDirection]);

  const handleSort = useCallback(
    (column: string) => {
      if (sortColumn === column) {
        setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortColumn(column);
        setSortDirection("asc");
      }
    },
    [sortColumn]
  );

  return {
    sortColumn,
    sortDirection,
    sortedRows,
    handleSort,
  };
}
