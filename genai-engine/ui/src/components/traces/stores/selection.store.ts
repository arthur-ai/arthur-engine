import { create } from "zustand/react";

type SelectionStore = {
  selection: {
    trace: string;
    span: string;
    session: string;
    user: string;
  };

  select: (type: keyof SelectionStore["selection"], id: string) => void;
  reset: () => void;
};

export const useSelectionStore = create<SelectionStore>()((set, get) => ({
  selection: {
    trace: "",
    span: "",
    session: "",
    user: "",
  },
  select: (type, id) => set({ selection: { ...get().selection, [type]: id } }),
  reset: () =>
    set({ selection: { trace: "", span: "", session: "", user: "" } }),
}));
