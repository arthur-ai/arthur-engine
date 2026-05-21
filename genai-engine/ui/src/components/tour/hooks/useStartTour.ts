import { useCallback } from "react";

import { toursEnabled } from "@/lib/tours-config";
import { useTourStore, type StartTourOptions } from "@/stores/tour.store";
import type { TourId } from "@/tours/registry";

export function useStartTour() {
  const startTour = useTourStore((state) => state.actions.startTour);
  const resumeTour = useTourStore((state) => state.actions.resumeTour);
  const dismissTour = useTourStore((state) => state.actions.dismissTour);
  const stopTour = useTourStore((state) => state.actions.stopTour);
  const completedTourIds = useTourStore((state) => state.completedTourIds);

  const start = useCallback(
    (tourId: TourId, options?: StartTourOptions) => {
      if (!toursEnabled) {
        return false;
      }
      return startTour(tourId, options);
    },
    [startTour]
  );

  const resume = useCallback(
    (tourId: TourId) => {
      if (!toursEnabled) {
        return false;
      }
      return resumeTour(tourId);
    },
    [resumeTour]
  );

  return {
    startTour: start,
    resumeTour: resume,
    dismissTour,
    stopTour,
    completedTourIds,
    toursEnabled,
  };
}
