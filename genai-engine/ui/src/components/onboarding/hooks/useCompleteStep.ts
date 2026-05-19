import { useCallback } from "react";

import { STEPS, type StepId } from "../steps";
import { useOnboardingStore } from "../stores/onboarding.store";

export const useCompleteStep = (stepId: StepId): (() => void) => {
  const status = useOnboardingStore((s) => s.status);
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const next = useOnboardingStore((s) => s.next);

  return useCallback(() => {
    if (status !== "active") return;
    if (STEPS[currentStep]?.id !== stepId) return;
    next("user_action");
  }, [status, currentStep, stepId, next]);
};
