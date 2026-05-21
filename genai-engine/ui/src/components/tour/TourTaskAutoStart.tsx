import { useEffect, useRef } from "react";

import { useStartTour } from "@/components/tour/hooks/useStartTour";
import { onboardingExerciseTaskId, toursEnabled } from "@/lib/tours-config";
import { useTourStore } from "@/stores/tour.store";

type Props = {
  taskId: string;
};

export function TourTaskAutoStart({ taskId }: Props) {
  const { toursEnabled: enabled } = useStartTour();
  const setRouteParams = useTourStore((state) => state.actions.setRouteParams);
  const hasCompletedTaskTour = useTourStore((state) => state.actions.hasCompletedTaskTour);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!enabled || !toursEnabled || !taskId || taskId !== onboardingExerciseTaskId || startedRef.current) {
      return;
    }

    if (hasCompletedTaskTour("onboarding", taskId)) {
      return;
    }

    setRouteParams({ taskId });

    // Ensure params are committed before the provider tick navigates.
    const started = useTourStore.getState().actions.startTour("onboarding", { stepId: "intro-adlc" });

    if (started) {
      startedRef.current = true;
    }
  }, [enabled, hasCompletedTaskTour, setRouteParams, taskId]);

  return null;
}
