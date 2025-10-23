import { createStore } from "@xstate/store";
import { createContext, useContext, useMemo } from "react";

import { IncomingFilter } from "../mapper";

const createFilterStore = () => {
  const store = createStore({
    context: {
      filters: [] as IncomingFilter[],
    },
    emits: {
      filtered: () => {},
    },
    on: {
      setFilters: (context, event: { filters: IncomingFilter[] }, enqueue) => {
        enqueue.emit.filtered();
        return {
          ...context,
          filters: event.filters,
        };
      },
    },
  });

  return store;
};

type FilterStore = ReturnType<typeof createFilterStore>;

const Context = createContext<FilterStore | null>(null);

export const useFilterStore = () => {
  const store = useContext(Context);

  if (!store) {
    throw new Error("useFilterStore must be used within a FilterStoreProvider");
  }
  return store;
};

export const FilterStoreProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const store = useMemo(() => createFilterStore(), []);
  return <Context.Provider value={store}>{children}</Context.Provider>;
};
