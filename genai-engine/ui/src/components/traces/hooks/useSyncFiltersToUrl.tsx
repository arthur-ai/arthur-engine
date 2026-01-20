import { parseAsJson, useQueryState } from "nuqs";
import { useEffect, useRef } from "react";
import { z } from "zod";

import type { IncomingFilter } from "../components/filtering/mapper";
import { useFilterStore } from "../stores/filter.store";

import { EVENT_NAMES, track } from "@/services/amplitude";

/**
 * Zod schema for validating filter objects from URL
 */
const filterSchema = z.array(
  z.object({
    name: z.string(),
    operator: z.string(),
    value: z.union([z.string(), z.array(z.string())]),
  })
);

/**
 * Hook to sync filters with URL search parameters
 * Reads filters from URL on mount and writes filters to URL when they change
 */
export function useSyncFiltersToUrl() {
  const [urlFilters, setUrlFilters] = useQueryState("filters", parseAsJson(filterSchema.parse).withDefault([]).withOptions({ history: "replace" }));

  const storeFilters = useFilterStore((state) => state.filters);
  const setStoreFilters = useFilterStore((state) => state.setFilters);

  const hasInitializedFromUrl = useRef(false);

  // Sync from URL to store on mount (only once)
  useEffect(() => {
    if (!hasInitializedFromUrl.current && urlFilters.length > 0) {
      setStoreFilters(urlFilters as IncomingFilter[]);
      track(EVENT_NAMES.TRACING_FILTERS_FROM_URL_LOADED, {
        filter_count: urlFilters.length,
        source: "url",
      });
      hasInitializedFromUrl.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync from store to URL when store changes
  useEffect(() => {
    // Skip the initial sync if we just loaded from URL
    if (!hasInitializedFromUrl.current) {
      hasInitializedFromUrl.current = true;
    }

    setUrlFilters(storeFilters.length > 0 ? storeFilters : null);
  }, [storeFilters, setUrlFilters]);
}
