import { type DataResultFilter } from "@arthur/unify-types";
import { create } from "zustand";

import { type TraceSpan } from "../../tracesTypes";
import { type FilterableField } from "../fields";
import { SPAN_FILTERS_STRATEGIES } from "../rules";
import { type MetricFilterSchema } from "../types";
import { filtersToRequest } from "../utils";

type FilterState = {
  filters: MetricFilterSchema[];
  requestFilters: DataResultFilter[];
  spans: Map<string, TraceSpan[]>;
};

type FilterActions = {
  setFilters: (filters: MetricFilterSchema[]) => void;
  /**
   * Checks if a span matches the filters (only span filters)
   * @param span - The span to check
   * @returns True if the span matches the filters, false otherwise
   */
  matches: (span: TraceSpan) => boolean;
  addTraceSpans: (traceId: string, spans: TraceSpan[]) => void;
};

export const useFilterStore = create<FilterState & FilterActions>()((set, get) => ({
  filters: [],
  requestFilters: [],
  spans: new Map(),
  setFilters: (filters) => set({ filters, requestFilters: filtersToRequest(filters) }),
  matches: (span) => {
    const { filters } = get();

    if (filters.length === 0) return false;

    // get only span filters
    const spanFilters = filters.filter((filter) => filter.name in SPAN_FILTERS_STRATEGIES);

    for (const filter of spanFilters) {
      const strategy = SPAN_FILTERS_STRATEGIES[filter.name as FilterableField];

      const result = strategy({ span, filter });

      if (!result) return false;
    }

    return true;
  },
  addTraceSpans: (traceId, spans) => set((state) => ({ spans: new Map([...state.spans, [traceId, spans]]) })),
}));

export const useTracesIds = () => {
  const spans = useFilterStore((state) => state.spans);

  return [...spans.keys()];
};
