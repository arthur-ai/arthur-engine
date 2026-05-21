import { useCallback } from "react";

import { useTourStore } from "@/stores/tour.store";
import { getActiveTour, getFlatSteps, type TourId } from "@/tours/registry";

export function useAdvanceTourStep() {
  const activeTourId = useTourStore((state) => state.activeTourId);
  const activeStepId = useTourStore((state) => state.activeStepId);
  const setStep = useTourStore((state) => state.actions.setStep);
  const completeTour = useTourStore((state) => state.actions.completeTour);

  const advance = useCallback(() => {
    if (!activeTourId || !activeStepId) {
      return;
    }

    const tour = getActiveTour(activeTourId as TourId);
    if (!tour) {
      return;
    }

    const flatSteps = getFlatSteps(tour);
    const currentIndex = flatSteps.findIndex((step) => step.id === activeStepId);

    if (currentIndex < 0) {
      return;
    }

    if (currentIndex >= flatSteps.length - 1) {
      completeTour(activeTourId);
      return;
    }

    setStep(flatSteps[currentIndex + 1].id);
  }, [activeStepId, activeTourId, completeTour, setStep]);

  return { advance };
}
