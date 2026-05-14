import { useCallback } from "react";

import { STEPS, type StepId } from "../steps";
import { useOnboardingStore } from "../stores/onboarding.store";

// Returns a callback that advances the tour iff it's active and this step is current
export const useCompleteStep = (stepId: StepId): (() => void) => {
  const status = useOnboardingStore((s) => s.status);
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const next = useOnboardingStore((s) => s.next);

  return useCallback(() => {
    if (status !== "active") return;
    if (STEPS[currentStep]?.id !== stepId) return;
    next();
  }, [status, currentStep, stepId, next]);
};
