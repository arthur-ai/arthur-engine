import { create } from "zustand";
import { persist } from "zustand/middleware";

import { getActiveTour, getFlatSteps, type TourId } from "@/tours/registry";

export type StartTourOptions = {
  stepId?: string;
  force?: boolean;
};

type TourPersistedState = {
  completedTourIds: string[];
  lastStepByTour: Record<string, string>;
  dismissedAt?: string;
};

type TourActions = {
  startTour: (tourId: TourId | string, options?: StartTourOptions) => boolean;
  setStep: (stepId: string) => void;
  stopTour: () => void;
  completeTour: (tourId: string) => void;
  dismissTour: (tourId: string) => void;
  resumeTour: (tourId: TourId | string) => boolean;
};

type TourState = TourPersistedState & {
  activeTourId: string | null;
  activeStepId: string | null;
  actions: TourActions;
};

export const useTourStore = create<TourState>()(
  persist(
    (set, get) => ({
      completedTourIds: [],
      lastStepByTour: {},
      dismissedAt: undefined,
      activeTourId: null,
      activeStepId: null,

      actions: {
        startTour: (tourId, options = {}) => {
          const { stepId, force = false } = options;
          const state = get();

          if (!force && state.completedTourIds.includes(tourId)) {
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

        stopTour: () => {
          set({ activeTourId: null, activeStepId: null });
        },

        completeTour: (tourId) => {
          const { completedTourIds, lastStepByTour } = get();
          const nextLastStepByTour = { ...lastStepByTour };
          delete nextLastStepByTour[tourId];

          set({
            activeTourId: null,
            activeStepId: null,
            completedTourIds: completedTourIds.includes(tourId) ? completedTourIds : [...completedTourIds, tourId],
            lastStepByTour: nextLastStepByTour,
          });
        },

        dismissTour: (tourId) => {
          get().actions.completeTour(tourId);
          set({ dismissedAt: new Date().toISOString() });
        },

        resumeTour: (tourId) => {
          const { lastStepByTour, completedTourIds } = get();

          if (completedTourIds.includes(tourId)) {
            return false;
          }

          const stepId = lastStepByTour[tourId];
          return get().actions.startTour(tourId, { stepId, force: true });
        },
      },
    }),
    {
      name: "arthur-tour-progress",
      version: 1,
      partialize: (state) => ({
        completedTourIds: state.completedTourIds,
        lastStepByTour: state.lastStepByTour,
        dismissedAt: state.dismissedAt,
      }),
    }
  )
);
