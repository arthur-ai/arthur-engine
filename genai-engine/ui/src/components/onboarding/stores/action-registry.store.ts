import { create } from "zustand";
import { devtools } from "zustand/middleware";

import type { MajorTaskId, StepId } from "../steps";

type Action = () => void;

interface ActionRegistryState {
  stepActions: Partial<Record<StepId, Action>>;
  majorTaskExits: Partial<Record<MajorTaskId, Action>>;
  registerStep: (id: StepId, fn: Action) => () => void;
  registerMajorTaskExit: (id: MajorTaskId, fn: Action) => () => void;
  runStep: (id: StepId) => boolean;
  runMajorTaskExit: (id: MajorTaskId) => boolean;
}

export const useActionRegistry = create<ActionRegistryState>()(
  devtools(
    (set, get) => ({
      stepActions: {},
      majorTaskExits: {},

      registerStep: (id, fn) => {
        set((state) => ({ stepActions: { ...state.stepActions, [id]: fn } }), false, `action-registry/register-step/${id}`);
        return () => {
          if (get().stepActions[id] !== fn) return;
          set(
            (state) => {
              const next = { ...state.stepActions };
              delete next[id];
              return { stepActions: next };
            },
            false,
            `action-registry/unregister-step/${id}`
          );
        };
      },

      registerMajorTaskExit: (id, fn) => {
        set((state) => ({ majorTaskExits: { ...state.majorTaskExits, [id]: fn } }), false, `action-registry/register-exit/${id}`);
        return () => {
          if (get().majorTaskExits[id] !== fn) return;
          set(
            (state) => {
              const next = { ...state.majorTaskExits };
              delete next[id];
              return { majorTaskExits: next };
            },
            false,
            `action-registry/unregister-exit/${id}`
          );
        };
      },

      runStep: (id) => {
        const fn = get().stepActions[id];
        if (!fn) return false;
        fn();
        return true;
      },

      runMajorTaskExit: (id) => {
        const fn = get().majorTaskExits[id];
        if (!fn) return false;
        fn();
        return true;
      },
    }),
    { name: "onboarding-action-registry" }
  )
);

export const runStepAction = (id: StepId): boolean => useActionRegistry.getState().runStep(id);
export const runMajorTaskExit = (id: MajorTaskId): boolean => useActionRegistry.getState().runMajorTaskExit(id);
