import { useEffect, useEffectEvent, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import type { IncomingFilter } from "../components/filtering/mapper";
import { useFilterStore } from "../stores/filter.store";

const FILTERS_URL_KEY = "filters";

/**
 * Serialize filters to URL-safe string
 */
function serializeFilters(filters: IncomingFilter[]): string {
  if (filters.length === 0) return "";
  return JSON.stringify(filters);
}

/**
 * Deserialize filters from URL string
 */
function deserializeFilters(filterString: string | null): IncomingFilter[] {
  if (!filterString) return [];
  try {
    const parsed = JSON.parse(filterString);
    // Validate that it's an array of filters
    if (Array.isArray(parsed)) {
      return parsed.filter(
        (f): f is IncomingFilter =>
          f &&
          typeof f === "object" &&
          typeof f.name === "string" &&
          typeof f.operator === "string" &&
          (typeof f.value === "string" || Array.isArray(f.value))
      );
    }
    return [];
  } catch {
    return [];
  }
}

/**
 * Hook to sync filters with URL search parameters
 * Reads filters from URL on mount and writes filters to URL when they change
 */
export function useSyncFiltersToUrl() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useFilterStore((state) => state.filters);
  const setFilters = useFilterStore((state) => state.setFilters);
  const isInitialMount = useRef(true);

  // Read filters from URL on initial mount
  useEffect(() => {
    const filtersParam = searchParams.get(FILTERS_URL_KEY);
    if (filtersParam) {
      const urlFilters = deserializeFilters(filtersParam);
      if (urlFilters.length > 0) {
        setFilters(urlFilters);
      }
    }
    isInitialMount.current = false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Write filters to URL when they change (but not on initial mount)
  const onFiltersChange = useEffectEvent((newFilters: IncomingFilter[]) => {
    if (isInitialMount.current) return;

    const newSearchParams = new URLSearchParams(searchParams);
    if (newFilters.length > 0) {
      newSearchParams.set(FILTERS_URL_KEY, serializeFilters(newFilters));
    } else {
      newSearchParams.delete(FILTERS_URL_KEY);
    }
    setSearchParams(newSearchParams, { replace: true });
  });

  useEffect(() => {
    if (!isInitialMount.current) {
      onFiltersChange(filters);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);
}
