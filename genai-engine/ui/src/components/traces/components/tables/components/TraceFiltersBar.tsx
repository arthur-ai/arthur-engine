import { type ContinuousEvalNameOptions, TextOperators, TracesFilterBar } from "@arthur/shared-components/traces";
import { useMemo, useState } from "react";

import { useFilterStore } from "../../../stores/filter.store";

import { useInfiniteContinuousEvals } from "@/components/live-evals/hooks/useContinuousEvals";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

const useContinuousEvalNameOptions = (): ContinuousEvalNameOptions => {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);

  const filters = useMemo(() => {
    const name = debouncedSearch.trim();
    return name ? [{ name: "name", operator: TextOperators.CONTAINS, value: name }] : [];
  }, [debouncedSearch]);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteContinuousEvals({ pageSize: 10, filters });

  const names = useMemo(() => [...new Set((data?.pages ?? []).flatMap((page) => page.evals ?? []).map((eval_) => eval_.name))], [data]);

  return {
    names,
    onSearch: setSearch,
    onLoadMore: () => void fetchNextPage(),
    hasMore: hasNextPage,
    isLoadingMore: isFetchingNextPage,
  };
};

/** The shared span-name search and filter modal, bound to the tracing filter store. */
export const TraceFiltersBar = () => {
  const filters = useFilterStore((state) => state.filters);
  const setFilters = useFilterStore((state) => state.setFilters);
  const continuousEvalNames = useContinuousEvalNameOptions();

  return <TracesFilterBar filters={filters} onFiltersChange={setFilters} continuousEvalNames={continuousEvalNames} />;
};
