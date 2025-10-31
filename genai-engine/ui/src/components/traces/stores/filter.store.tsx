// filterStore.ts
import { create, StoreApi, UseBoundStore } from "zustand";
import { devtools, subscribeWithSelector } from "zustand/middleware";
import type { IncomingFilter } from "../components/filtering/mapper";
import { createContext, use, useState } from "react";

export interface FilterState {
  filters: IncomingFilter[];

  // actions
  setFilters: (filters: IncomingFilter[]) => void;
  resetFilters: () => void;
}

// If you don't want devtools, remove the devtools() wrapper.
const createFilterStore = () =>
  create<FilterState>()(
    devtools(
      subscribeWithSelector((set, get) => ({
        filters: [],

        setFilters: (filters) => {
          set({ filters }, false, "filters/setFilters");
        },

        resetFilters: () => {
          set({ filters: [] }, false, "filters/resetFilters");
        },
      })),
      { name: "filter-store" }
    )
  );

export type FilterStore = UseBoundStore<StoreApi<FilterState>>;

const Context = createContext<ReturnType<typeof createFilterStore> | null>(
  null
);

export function useFilterStore(): FilterState;
export function useFilterStore<T>(
  selector: (state: FilterState) => T,
  equalityFn?: (a: T, b: T) => boolean
): T;

export function useFilterStore<T>(
  selector?: (state: FilterState) => T,
  equalityFn?: (a: T, b: T) => boolean
) {
  const store = use(Context);
  if (!store) {
    throw new Error("useFilterStore must be used within a FilterStoreProvider");
  }

  // @ts-expect-error - TS can’t perfectly narrow both call forms here, but the overloads handle it for callers.
  return store(selector, equalityFn);
}

export const FilterStoreProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [store] = useState(() => createFilterStore());

  return <Context.Provider value={store}>{children}</Context.Provider>;
};
