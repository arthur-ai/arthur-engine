import { useCallback, useEffect, useMemo, useState } from "react";

import { SEARCH_DEBOUNCE_MS } from "@/constants/datasetConstants";
import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

export interface UseDatasetSearchReturn {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  filteredRows: DatasetVersionRowResponse[];
  handleClearSearch: () => void;
}

export function useDatasetSearch(
  rows: DatasetVersionRowResponse[]
): UseDatasetSearchReturn {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [searchQuery]);

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
