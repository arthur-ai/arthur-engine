import { create } from "zustand";
import { devtools } from "zustand/middleware";

import type { StepId } from "../steps";

type StepAction = () => void;

interface ActionRegistryState {
  actions: Partial<Record<StepId, StepAction>>;
  register: (id: StepId, fn: StepAction) => () => void;
  runAction: (id: StepId) => boolean;
}

export const useActionRegistry = create<ActionRegistryState>()(
  devtools(
    (set, get) => ({
      actions: {},

      register: (id, fn) => {
        set((state) => ({ actions: { ...state.actions, [id]: fn } }), false, `action-registry/register/${id}`);
        return () => {
          if (get().actions[id] !== fn) return;
          set(
            (state) => {
              const next = { ...state.actions };
              delete next[id];
              return { actions: next };
            },
            false,
            `action-registry/unregister/${id}`
          );
        };
      },

      runAction: (id) => {
        const fn = get().actions[id];
        if (!fn) return false;
        fn();
        return true;
      },
    }),
    { name: "onboarding-action-registry" }
  )
);

export const runStepAction = (id: StepId): boolean => useActionRegistry.getState().runAction(id);
