import { useCallback, useMemo, useState } from "react";

import { SEARCH_DEBOUNCE_MS } from "@/constants/datasetConstants";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

export interface UseDatasetSearchReturn {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  filteredRows: DatasetVersionRowResponse[];
  handleClearSearch: () => void;
}

export function useDatasetSearch(rows: DatasetVersionRowResponse[]): UseDatasetSearchReturn {
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearchQuery = useDebouncedValue(searchQuery, SEARCH_DEBOUNCE_MS);

  const filteredRows = useMemo(() => {
    if (!debouncedSearchQuery.trim()) {
      return rows;
    }

    const lowerQuery = debouncedSearchQuery.toLowerCase();

    return rows.filter((row) => {
      return row.data.some((col) => {
        const value = col.column_value?.toLowerCase() || "";
        return value.includes(lowerQuery);
      });
    });
  }, [rows, debouncedSearchQuery]);

  const handleClearSearch = useCallback(() => {
    setSearchQuery("");
  }, []);

  return {
    searchQuery,
    setSearchQuery,
    filteredRows,
    handleClearSearch,
  };
}
