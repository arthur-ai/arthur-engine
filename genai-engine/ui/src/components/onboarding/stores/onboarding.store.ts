import { create } from "zustand";
import { devtools, persist, subscribeWithSelector } from "zustand/middleware";

import {
  type OnboardingSnapshot,
  type OnboardingSource,
  trackMajorTaskCompleted,
  trackMajorTaskSkipped,
  trackOnboardingCompleted,
  trackOnboardingDismissed,
  trackOnboardingReplayed,
  trackOnboardingReset,
  trackOnboardingStarted,
  trackPanelToggled,
  trackStepCompleted,
  trackStepSkipped,
} from "../analytics";
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
  next: (source?: OnboardingSource) => void;
  goTo: (step: number) => void;
  skipToNext: (source?: OnboardingSource) => void;
  dismiss: (source?: OnboardingSource) => void;
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

const snapshotAt = (state: PersistedState, stepIndex: number): OnboardingSnapshot => ({
  step_index: stepIndex,
  completed_count: state.completedSteps.length,
  skipped_count: state.skippedSteps.length,
});

export const useOnboardingStore = create<OnboardingStore>()(
  devtools(
    subscribeWithSelector(
      persist(
        (set, get) => ({
          ...initialState,

          start: () => {
            const state = get();
            if (state.status === "completed") return;
            const isResume = state.status !== "idle" && state.currentStep > 0;
            const nextCurrentStep = state.status === "idle" ? 0 : state.currentStep;
            set({ status: "active", currentStep: nextCurrentStep }, false, "onboarding/start");
            trackOnboardingStarted(snapshotAt(get(), nextCurrentStep), isResume);
          },

          next: (source: OnboardingSource = "unknown") => {
            const state = get();
            const { currentStep, completedSteps, skippedSteps } = state;
            const currentId = STEPS[currentStep]?.id;
            const newCompleted = currentId && !completedSteps.includes(currentId) ? [...completedSteps, currentId] : completedSteps;
            // Finishing a previously-skipped step promotes it from "skipped" to "completed".
            const newSkipped = currentId ? skippedSteps.filter((id) => id !== currentId) : skippedSteps;

            const nextStep = currentStep + 1;
            const currentTask = currentId ? findMajorTaskForStep(currentId) : undefined;
            const crossesBoundary = !!currentTask && crossesMajorTaskBoundary(currentStep, nextStep);
            if (crossesBoundary && currentTask) {
              runMajorTaskExit(currentTask.id);
            }

            trackStepCompleted(snapshotAt(state, currentStep), source);
            if (crossesBoundary) {
              trackMajorTaskCompleted(snapshotAt(state, currentStep));
            }

            if (nextStep >= STEPS.length) {
              set(
                { status: "completed", currentStep: STEPS.length - 1, completedSteps: newCompleted, skippedSteps: newSkipped },
                false,
                "onboarding/next-complete"
              );
              trackOnboardingCompleted(snapshotAt(get(), STEPS.length - 1));
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

          skipToNext: (source: OnboardingSource = "unknown") => {
            const initial = get();
            const startIndex = initial.currentStep;
            const startId = STEPS[startIndex]?.id;
            if (!startId) return;

            const currentTask = findMajorTaskForStep(startId);
            if (currentTask) runMajorTaskExit(currentTask.id);

            const { completedSteps, skippedSteps } = initial;
            const targetIndex = firstStepOfNextMajorTask(startIndex);
            const skipEnd = targetIndex >= STEPS.length ? STEPS.length : targetIndex;

            const batch: StepId[] = [];
            for (let i = startIndex; i < skipEnd; i++) {
              const id = STEPS[i]?.id;
              if (id && !completedSteps.includes(id) && !batch.includes(id)) {
                batch.push(id);
              }
            }
            const newSkipped = [...skippedSteps];
            for (const id of batch) {
              if (!newSkipped.includes(id)) newSkipped.push(id);
            }

            for (const id of batch) {
              const idx = STEPS.findIndex((s) => s.id === id);
              trackStepSkipped(snapshotAt(initial, idx), source, batch);
            }
            if (currentTask) {
              trackMajorTaskSkipped(snapshotAt(initial, startIndex), batch);
            }

            if (targetIndex >= STEPS.length) {
              set({ status: "dismissed", skippedSteps: newSkipped }, false, "onboarding/skip-to-end");
              trackOnboardingDismissed(snapshotAt(get(), startIndex), "skip_to_end");
              return;
            }

            set({ currentStep: targetIndex, skippedSteps: newSkipped }, false, "onboarding/skip-to-step");
          },

          dismiss: (source: OnboardingSource = "unknown") => {
            const state = get();
            set({ status: "dismissed" }, false, "onboarding/dismiss");
            trackOnboardingDismissed(snapshotAt(state, state.currentStep), source);
          },

          restart: () => {
            const state = get();
            set({ status: "active" }, false, "onboarding/restart");
            trackOnboardingReplayed(snapshotAt(state, state.currentStep), "dismissed");
          },

          reset: () => {
            const prior = get();
            set({ ...initialState, panelCollapsed: prior.panelCollapsed }, false, "onboarding/reset");
            const fresh = get();
            if (prior.status === "completed") {
              trackOnboardingReplayed(snapshotAt(fresh, fresh.currentStep), "completed");
            } else {
              trackOnboardingReset(snapshotAt(fresh, fresh.currentStep));
            }
          },

          setPanelCollapsed: (collapsed) => {
            set({ panelCollapsed: collapsed }, false, "onboarding/setPanelCollapsed");
            const state = get();
            trackPanelToggled(snapshotAt(state, state.currentStep), collapsed);
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
