import { create } from "zustand";

import { Level } from "../constants";

type Context = {
  type: Level;
  ids: string[];
};

type PaginationContextActions = {
  setContext: (context: Context) => void;
};

type PaginationContextState = {
  context: Context;
  actions: PaginationContextActions;
};

export const usePaginationContext = create<PaginationContextState>()((set) => ({
  context: {
    type: "trace",
    ids: [],
  },
  actions: {
    setContext: (context) => set({ context }),
  },
}));
