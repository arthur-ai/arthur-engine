import { useMemo } from "react";

import { useTourStore } from "@/stores/tour.store";
import { getActiveTour, getFlatSteps, type TourId } from "@/tours/registry";

export function useCurrentTourStep() {
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
    return flatSteps.find((step) => step.id === activeStepId) ?? null;
  }, [activeTourId, activeStepId]);
}
