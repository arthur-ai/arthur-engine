// filterStore.ts
import { createContext, use, useEffect, useState } from "react";
import { create, StoreApi, UseBoundStore } from "zustand";
import { devtools, subscribeWithSelector } from "zustand/middleware";

import type { IncomingFilter } from "../components/filtering/mapper";
import { TimeRange } from "../constants";

export interface FilterState {
  filters: IncomingFilter[];
  timeRange: TimeRange;

  setFilters: (filters: IncomingFilter[]) => void;
  setTimeRange: (timeRange: TimeRange) => void;
  resetFilters: () => void;
}

const createFilterStore = (timeRange: TimeRange) =>
  create<FilterState>()(
    devtools(
      subscribeWithSelector((set) => ({
        filters: [],
        timeRange,

        setFilters: (filters) => {
          set({ filters }, false, "filters/setFilters");
        },

        resetFilters: () => {
          set({ filters: [] }, false, "filters/resetFilters");
        },

        setTimeRange: (timeRange) => {
          set({ timeRange }, false, "filters/setTimeRange");
        },
      })),
      { name: "filter-store" }
    )
  );

export type FilterStore = UseBoundStore<StoreApi<FilterState>>;

const Context = createContext<ReturnType<typeof createFilterStore> | null>(null);

export function useFilterStore(): FilterState;
export function useFilterStore<T>(selector: (state: FilterState) => T, equalityFn?: (a: T, b: T) => boolean): T;

export function useFilterStore<T>(selector?: (state: FilterState) => T, equalityFn?: (a: T, b: T) => boolean) {
  const store = use(Context);
  if (!store) {
    throw new Error("useFilterStore must be used within a FilterStoreProvider");
  }

  // @ts-expect-error - TS can’t perfectly narrow both call forms here, but the overloads handle it for callers.
  return store(selector, equalityFn);
}

export const FilterStoreProvider = ({ children, timeRange }: { children: React.ReactNode; timeRange: TimeRange }) => {
  const [store] = useState(() => createFilterStore(timeRange));

  useEffect(() => {
    store.setState({ timeRange });
  }, [store, timeRange]);

  return <Context.Provider value={store}>{children}</Context.Provider>;
};
