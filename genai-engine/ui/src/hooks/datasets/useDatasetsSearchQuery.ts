import { useEffect, useState, useRef } from "react";

import { SEARCH_DEBOUNCE_MS } from "@/constants/datasetConstants";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

export const useDatasetsSearchQuery = (onDebouncedChange?: () => void) => {
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearchQuery = useDebouncedValue(searchQuery, SEARCH_DEBOUNCE_MS);
  const isInitialMount = useRef(true);

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    onDebouncedChange?.();
  }, [debouncedSearchQuery, onDebouncedChange]);

  return {
    searchQuery,
    setSearchQuery,
    debouncedSearchQuery,
  };
};
