import { create } from "zustand";
import { persist } from "zustand/middleware";

import { getActiveTour, getFlatSteps, type TourId } from "@/tours/registry";

export type StartTourOptions = {
  stepId?: string;
  force?: boolean;
};

const taskTourKey = (tourId: string, taskId: string) => `${tourId}:${taskId}`;

type TourPersistedState = {
  completedTourIds: string[];
  completedTaskTourKeys: string[];
  lastStepByTour: Record<string, string>;
  dismissedAt?: string;
};

type TourActions = {
  startTour: (tourId: TourId | string, options?: StartTourOptions) => boolean;
  setStep: (stepId: string) => void;
  setRouteParams: (params: Record<string, string>) => void;
  showGuidance: () => void;
  minimizeGuidance: () => void;
  stopTour: () => void;
  completeTour: (tourId: string) => void;
  dismissTour: (tourId: string) => void;
  resumeTour: (tourId: TourId | string) => boolean;
  hasCompletedTaskTour: (tourId: string, taskId: string) => boolean;
};

type TourState = TourPersistedState & {
  activeTourId: string | null;
  activeStepId: string | null;
  guidanceVisible: boolean;
  routeParams: Record<string, string>;
  actions: TourActions;
};

export const useTourStore = create<TourState>()(
  persist(
    (set, get) => ({
      completedTourIds: [],
      completedTaskTourKeys: [],
      lastStepByTour: {},
      dismissedAt: undefined,
      activeTourId: null,
      activeStepId: null,
      guidanceVisible: true,
      routeParams: {},

      actions: {
        startTour: (tourId, options = {}) => {
          const { stepId, force = false } = options;
          const state = get();
          const taskId = state.routeParams.taskId;

          if (!force && state.completedTourIds.includes(tourId)) {
            return false;
          }

          if (!force && taskId && state.completedTaskTourKeys.includes(taskTourKey(tourId, taskId))) {
            return false;
          }

          const tour = getActiveTour(tourId);
          if (!tour) {
            return false;
          }

          const flatSteps = getFlatSteps(tour);
          const resolvedStepId = stepId ?? flatSteps[0]?.id;

          if (!resolvedStepId) {
            return false;
          }

          set({
            activeTourId: tourId,
            activeStepId: resolvedStepId,
            guidanceVisible: true,
            lastStepByTour: {
              ...state.lastStepByTour,
              [tourId]: resolvedStepId,
            },
          });

          return true;
        },

        setStep: (stepId) => {
          const { activeTourId, lastStepByTour } = get();
          if (!activeTourId) {
            return;
          }

          set({
            activeStepId: stepId,
            lastStepByTour: {
              ...lastStepByTour,
              [activeTourId]: stepId,
            },
          });
        },

        setRouteParams: (params) => {
          set({ routeParams: params });
        },

        showGuidance: () => {
          set({ guidanceVisible: true });
        },

        minimizeGuidance: () => {
          set({ guidanceVisible: false });
        },

        stopTour: () => {
          set({ activeTourId: null, activeStepId: null, guidanceVisible: true });
        },

        completeTour: (tourId) => {
          const { completedTourIds, completedTaskTourKeys, lastStepByTour, routeParams } = get();
          const nextLastStepByTour = { ...lastStepByTour };
          delete nextLastStepByTour[tourId];

          const taskId = routeParams.taskId;
          const nextCompletedTaskTourKeys =
            taskId && !completedTaskTourKeys.includes(taskTourKey(tourId, taskId))
              ? [...completedTaskTourKeys, taskTourKey(tourId, taskId)]
              : completedTaskTourKeys;

          set({
            activeTourId: null,
            activeStepId: null,
            guidanceVisible: true,
            completedTourIds: completedTourIds.includes(tourId) ? completedTourIds : [...completedTourIds, tourId],
            completedTaskTourKeys: nextCompletedTaskTourKeys,
            lastStepByTour: nextLastStepByTour,
          });
        },

        dismissTour: (tourId) => {
          get().actions.completeTour(tourId);
          set({ dismissedAt: new Date().toISOString() });
        },

        resumeTour: (tourId) => {
          const { lastStepByTour, completedTourIds, completedTaskTourKeys, routeParams } = get();
          const taskId = routeParams.taskId;

          if (completedTourIds.includes(tourId)) {
            return false;
          }

          if (taskId && completedTaskTourKeys.includes(taskTourKey(tourId, taskId))) {
            return false;
          }

          const stepId = lastStepByTour[tourId];
          return get().actions.startTour(tourId, { stepId, force: true });
        },

        hasCompletedTaskTour: (tourId, taskId) => {
          return get().completedTaskTourKeys.includes(taskTourKey(tourId, taskId));
        },
      },
    }),
    {
      name: "arthur-tour-progress",
      version: 2,
      partialize: (state) => ({
        completedTourIds: state.completedTourIds,
        completedTaskTourKeys: state.completedTaskTourKeys,
        lastStepByTour: state.lastStepByTour,
        dismissedAt: state.dismissedAt,
      }),
      migrate: (persistedState, version) => {
        const state = persistedState as TourPersistedState;

        if (version < 2) {
          return {
            ...state,
            completedTaskTourKeys: state.completedTaskTourKeys ?? [],
          };
        }

        return state;
      },
    }
  )
);
