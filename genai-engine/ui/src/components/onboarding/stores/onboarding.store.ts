import { create } from "zustand";
import { devtools, persist, subscribeWithSelector } from "zustand/middleware";

import { findMajorTaskForStep, MAJOR_TASKS, STEPS, type StepId } from "../steps";

import { runMajorTaskExit } from "./action-registry.store";

export type TourStatus = "idle" | "active" | "paused" | "dismissed" | "completed";

interface PersistedState {
  status: TourStatus;
  currentStep: number;
  completedSteps: StepId[];
  skippedSteps: StepId[];
  panelCollapsed: boolean;
}

export interface OnboardingStore extends PersistedState {
  start: () => void;
  next: () => void;
  goTo: (step: number) => void;
  skipToNext: () => void;
  dismiss: () => void;
  restart: () => void;
  reset: () => void;
  setPanelCollapsed: (collapsed: boolean) => void;
}

const initialState: PersistedState = {
  status: "idle",
  currentStep: 0,
  completedSteps: [],
  skippedSteps: [],
  panelCollapsed: true,
};

// Returns STEPS.length when there is no next major task.
const firstStepOfNextMajorTask = (stepIndex: number): number => {
  const currentId = STEPS[stepIndex]?.id;
  if (!currentId) return STEPS.length;
  const currentTask = findMajorTaskForStep(currentId);
  if (!currentTask) return STEPS.length;
  const currentTaskIdx = MAJOR_TASKS.findIndex((t) => t.id === currentTask.id);
  const nextTask = MAJOR_TASKS[currentTaskIdx + 1];
  if (!nextTask) return STEPS.length;
  const firstNextStep = nextTask.subtaskIds[0];
  return STEPS.findIndex((s) => s.id === firstNextStep);
};

const crossesMajorTaskBoundary = (fromIndex: number, toIndex: number): boolean => {
  const fromId = STEPS[fromIndex]?.id;
  const toId = STEPS[toIndex]?.id;
  if (!fromId) return false;
  const fromTask = findMajorTaskForStep(fromId);
  if (!fromTask) return false;
  if (!toId) return true; // moving past the last step = leaving the final major task
  const toTask = findMajorTaskForStep(toId);
  return !!toTask && toTask.id !== fromTask.id;
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
            const currentTask = currentId ? findMajorTaskForStep(currentId) : undefined;
            if (currentTask && crossesMajorTaskBoundary(currentStep, nextStep)) {
              runMajorTaskExit(currentTask.id);
            }

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
            const { currentStep } = get();
            if (step === currentStep) return;
            const currentId = STEPS[currentStep]?.id;
            const targetId = STEPS[step]?.id;
            if (currentId && targetId) {
              const currentTask = findMajorTaskForStep(currentId);
              const targetTask = findMajorTaskForStep(targetId);
              if (currentTask && targetTask && currentTask.id !== targetTask.id) {
                runMajorTaskExit(currentTask.id);
              }
            }
            set({ currentStep: step }, false, "onboarding/goTo");
          },

          skipToNext: () => {
            const startIndex = get().currentStep;
            const startId = STEPS[startIndex]?.id;
            if (!startId) return;

            const currentTask = findMajorTaskForStep(startId);
            if (currentTask) runMajorTaskExit(currentTask.id);

            const { completedSteps, skippedSteps } = get();
            const targetIndex = firstStepOfNextMajorTask(startIndex);

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

            if (targetIndex >= STEPS.length) {
              const newSkipped = collectSkipped(startIndex, STEPS.length);
              set({ status: "dismissed", skippedSteps: newSkipped }, false, "onboarding/skip-to-end");
              return;
            }

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
            set({ ...initialState, panelCollapsed: get().panelCollapsed }, false, "onboarding/reset");
          },

          setPanelCollapsed: (collapsed) => {
            set({ panelCollapsed: collapsed }, false, "onboarding/setPanelCollapsed");
          },
        }),
        {
          name: "arthur-onboarding-tour",
          partialize: (state): PersistedState => ({
            status: state.status,
            currentStep: state.currentStep,
            completedSteps: state.completedSteps,
            skippedSteps: state.skippedSteps,
            panelCollapsed: state.panelCollapsed,
          }),
        }
      )
    ),
    { name: "onboarding-store" }
  )
);
