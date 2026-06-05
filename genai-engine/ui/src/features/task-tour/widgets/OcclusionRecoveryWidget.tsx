import { useEffect } from "react";

import { dismissOverlay } from "../dismissOverlay";

import { useTourEngine } from "@/features/tour";
import { track } from "@/services/amplitude";

/**
 * Headless auto-recovery for occluded tour targets. When the engine reports the
 * active target is covered (`target:occluded`), it makes one attempt to clear
 * it — closing any registered occluder that drifted open mid-step AND
 * generically dismissing the covering surface ({@link dismissOverlay}: Escape /
 * backdrop) so we recover modals/drawers the tour never registered — then
 * re-checking. If a `target:revealed` follows, the target is back; otherwise the
 * contextual "bring this into view" affordance (driven separately by
 * `useTargetOcclusion` in the checklist) stays shown and an
 * `occlusion-unrecovered` event flags the blocker for follow-up.
 *
 * The `target:occluded` / `target:revealed` events are already forwarded to
 * analytics by the analytics plugin; this widget adds the recovered/unrecovered
 * outcome (with `viaUserAction`) so the funnel distinguishes auto-clears from
 * blockers we don't yet know how to close.
 */
const VERIFY_AFTER_MS = 400;

export function OcclusionRecoveryWidget() {
  const engine = useTourEngine();

  useEffect(() => {
    let attemptedStepKey: string | null = null;
    let pending: { key: string; occluderId: string } | null = null;
    let rafOuter = 0;
    let rafInner = 0;
    let verifyTimer = 0;

    const keyOf = (event: { sectionId: string; stepId: string }) => `${event.sectionId}.${event.stepId}`;
    const cancelTimers = () => {
      if (typeof window === "undefined") return;
      window.cancelAnimationFrame(rafOuter);
      window.cancelAnimationFrame(rafInner);
      window.clearTimeout(verifyTimer);
    };

    const onOccluded = (event: { sectionId: string; stepId: string; occluder: Element | null; occluderId: string }) => {
      const key = keyOf(event);
      // One auto-attempt per step; a re-fire just leaves the affordance up.
      if (attemptedStepKey === key || typeof window === "undefined") return;
      attemptedStepKey = key;
      pending = { key, occluderId: event.occluderId };

      // (a) close any registered occluder (e.g. the URL-driven trace drawer)...
      engine.reconcileActiveSurfaces();
      // ...and (b) generically dismiss the covering surface for everything else
      // (standard MUI modals/drawers), so presentational components need no
      // tour-specific registration.
      dismissOverlay(event.occluder);
      // (b) re-check after the close settles (two frames). A successful clear
      // emits `target:revealed` (also fired by ActiveTargetRefresh's mutation
      // re-check when the panel unmounts), which `onRevealed` records.
      rafOuter = window.requestAnimationFrame(() => {
        rafInner = window.requestAnimationFrame(() => {
          engine.recheckOcclusion();
          verifyTimer = window.setTimeout(() => {
            if (pending && pending.key === key) {
              track("task-tour.occlusion-unrecovered", { sectionId: event.sectionId, stepId: event.stepId, occluderId: pending.occluderId });
              pending = null;
            }
          }, VERIFY_AFTER_MS);
        });
      });
    };

    const onRevealed = (event: { sectionId: string; stepId: string }) => {
      if (pending && pending.key === keyOf(event)) {
        track("task-tour.occlusion-recovered", {
          sectionId: event.sectionId,
          stepId: event.stepId,
          occluderId: pending.occluderId,
          viaUserAction: false,
        });
        pending = null;
        cancelTimers();
      }
    };

    const onStepLeft = () => {
      attemptedStepKey = null;
      pending = null;
      cancelTimers();
    };

    engine.on("target:occluded", onOccluded);
    engine.on("target:revealed", onRevealed);
    engine.on("step:left", onStepLeft);
    return () => {
      engine.off("target:occluded", onOccluded);
      engine.off("target:revealed", onRevealed);
      engine.off("step:left", onStepLeft);
      cancelTimers();
    };
  }, [engine]);

  return null;
}
