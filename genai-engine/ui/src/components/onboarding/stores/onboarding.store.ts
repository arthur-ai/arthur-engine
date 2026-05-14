import { create } from "zustand";
import { devtools, persist, subscribeWithSelector } from "zustand/middleware";

import { SKIP_TO_END, STEPS, type StepId } from "../steps";

import { runStepAction } from "./action-registry.store";

export type TourStatus = "idle" | "active" | "paused" | "dismissed" | "completed";

interface PersistedState {
  status: TourStatus;
  currentStep: number;
  completedSteps: StepId[];
  skippedSteps: StepId[];
}

export interface OnboardingStore extends PersistedState {
  start: () => void;
  next: () => void;
  goTo: (step: number) => void;
  skipToNext: () => void;
  dismiss: () => void;
  restart: () => void;
  reset: () => void;
}

const initialState: PersistedState = {
  status: "idle",
  currentStep: 0,
  completedSteps: [],
  skippedSteps: [],
};

export const useOnboardingStore = create<OnboardingStore>()(
  devtools(
    subscribeWithSelector(
      persist(
        (set, get) => ({
          ...initialState,

          start: () => {
            const { status } = get();
            if (status === "completed") return;
            set({ status: "active", currentStep: status === "idle" ? 0 : get().currentStep }, false, "onboarding/start");
          },

          next: () => {
            const { currentStep, completedSteps, skippedSteps } = get();
            const currentId = STEPS[currentStep]?.id;
            const newCompleted = currentId && !completedSteps.includes(currentId) ? [...completedSteps, currentId] : completedSteps;
            // Finishing a previously-skipped step promotes it from "skipped" to "completed".
            const newSkipped = currentId ? skippedSteps.filter((id) => id !== currentId) : skippedSteps;

            const nextStep = currentStep + 1;
            if (nextStep >= STEPS.length) {
              set(
                { status: "completed", currentStep: STEPS.length - 1, completedSteps: newCompleted, skippedSteps: newSkipped },
                false,
                "onboarding/next-complete"
              );
              return;
            }
            set({ currentStep: nextStep, completedSteps: newCompleted, skippedSteps: newSkipped }, false, "onboarding/next");
          },

          goTo: (step) => {
            if (step < 0 || step >= STEPS.length) return;
            set({ currentStep: step }, false, "onboarding/goTo");
          },

          skipToNext: () => {
            const startIndex = get().currentStep;
            const stepConfig = STEPS[startIndex];
            if (!stepConfig?.skipTo) return;

            // Cleanup action may itself advance the store (via completeStep), so re-read after.
            if (stepConfig.runActionOnSkip) {
              runStepAction(stepConfig.id);
            }
            const { completedSteps, skippedSteps } = get();
            const collectSkipped = (fromIdx: number, toIdx: number): StepId[] => {
              const next = [...skippedSteps];
              for (let i = fromIdx; i < toIdx; i++) {
                const id = STEPS[i]?.id;
                if (id && !completedSteps.includes(id) && !next.includes(id)) {
                  next.push(id);
                }
              }
              return next;
            };

            if (stepConfig.skipTo === SKIP_TO_END) {
              const newSkipped = collectSkipped(startIndex, STEPS.length);
              set({ status: "dismissed", skippedSteps: newSkipped }, false, "onboarding/skip-to-end");
              return;
            }

            const targetIndex = STEPS.findIndex((s) => s.id === stepConfig.skipTo);
            if (targetIndex < 0) return;

            const newSkipped = collectSkipped(startIndex, targetIndex);
            set({ currentStep: targetIndex, skippedSteps: newSkipped }, false, "onboarding/skip-to-step");
          },

          dismiss: () => {
            set({ status: "dismissed" }, false, "onboarding/dismiss");
          },

          restart: () => {
            set({ status: "active" }, false, "onboarding/restart");
          },

          reset: () => {
            set(initialState, false, "onboarding/reset");
          },
        }),
        {
          name: "arthur-onboarding-tour",
          partialize: (state): PersistedState => ({
            status: state.status,
            currentStep: state.currentStep,
            completedSteps: state.completedSteps,
            skippedSteps: state.skippedSteps,
          }),
        }
      )
    ),
    { name: "onboarding-store" }
  )
);
