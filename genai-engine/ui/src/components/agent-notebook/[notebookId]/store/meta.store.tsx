import { create } from "zustand/react";

type MetaActions = {
  setBaseline: (hash: string) => void;
  setEdited: (edited: boolean) => void;
};

type MetaStore = {
  actions: MetaActions;

  baselineHash: string;
  edited: boolean;
};

export const useMetaStore = create<MetaStore>((set) => ({
  actions: {
    setBaseline: (hash) => set({ baselineHash: hash, edited: false }),
    setEdited: (edited) => set({ edited }),
  },
  baselineHash: "",
  edited: false,
}));
