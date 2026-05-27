import type { ComponentType } from "react";

import { useTourState } from "./useTour";

export interface StepMatcher {
  sectionId: string;
  stepId?: string;
}

/**
 * Mounts `Component` only while the engine is on the matching step. Pass
 * `stepId` to match a specific step; omit it to match any step in the
 * section.
 */
export function withTourStep<P extends object>(Component: ComponentType<P>, matcher: StepMatcher): ComponentType<P> {
  function StepWrapper(props: P) {
    const state = useTourState();
    if (state.status !== "step") return null;
    if (state.sectionId !== matcher.sectionId) return null;
    if (matcher.stepId && state.stepId !== matcher.stepId) return null;
    return <Component {...props} />;
  }
  StepWrapper.displayName = `withTourStep(${Component.displayName ?? Component.name ?? "Component"})`;
  return StepWrapper;
}
