import { useMemo } from "react";

import { useTourStore } from "@/stores/tour.store";
import { getActiveTour, getFlatSteps, type TourId } from "@/tours/registry";
import type { AnyTourEvents, TourStep } from "@/tours/types";

export type TourStepStatus = "completed" | "current" | "upcoming";

export type TourStepProgress = TourStep<AnyTourEvents> & {
  status: TourStepStatus;
  flatIndex: number;
};

export type TourSectionProgress = {
  id: string;
  title: string;
  steps: TourStepProgress[];
  completedCount: number;
  totalCount: number;
  isComplete: boolean;
};

export type TourProgress = {
  tourId: string;
  tourTitle: string;
  sections: TourSectionProgress[];
  currentStepId: string;
  currentIndex: number;
  totalSteps: number;
  completedCount: number;
};

export function useTourProgress(): TourProgress | null {
  const activeTourId = useTourStore((state) => state.activeTourId);
  const activeStepId = useTourStore((state) => state.activeStepId);

  return useMemo(() => {
    if (!activeTourId || !activeStepId) {
      return null;
    }

    const tour = getActiveTour(activeTourId as TourId);
    if (!tour) {
      return null;
    }

    const flatSteps = getFlatSteps(tour);
    const currentIndex = flatSteps.findIndex((step) => step.id === activeStepId);

    if (currentIndex < 0) {
      return null;
    }

    const sections: TourSectionProgress[] = tour.sections.map((section) => {
      const steps: TourStepProgress[] = section.steps.map((step) => {
        const flatIndex = flatSteps.findIndex((flatStep) => flatStep.id === step.id);
        let status: TourStepStatus = "upcoming";

        if (flatIndex < currentIndex) {
          status = "completed";
        } else if (flatIndex === currentIndex) {
          status = "current";
        }

        return { ...step, status, flatIndex };
      });

      const completedCount = steps.filter((step) => step.status === "completed").length;

      return {
        id: section.id,
        title: section.title,
        steps,
        completedCount,
        totalCount: steps.length,
        isComplete: completedCount === steps.length,
      };
    });

    return {
      tourId: tour.id,
      tourTitle: "Product tour",
      sections,
      currentStepId: activeStepId,
      currentIndex,
      totalSteps: flatSteps.length,
      completedCount: currentIndex,
    };
  }, [activeStepId, activeTourId]);
}
