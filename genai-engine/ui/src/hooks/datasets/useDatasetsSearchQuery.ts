import { useEffect, useState } from "react";

import { SEARCH_DEBOUNCE_MS } from "@/constants/datasetConstants";

export const useDatasetsSearchQuery = (onDebouncedChange?: () => void) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
      onDebouncedChange?.();
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [searchQuery, onDebouncedChange]);

  return {
    searchQuery,
    setSearchQuery,
    debouncedSearchQuery,
  };
};
