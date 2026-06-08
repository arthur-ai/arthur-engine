import { useCallback, useEffect, useState } from "react";

import { useTour, useTourEngine } from "../useTour";
import { useTourEvent } from "../useTourEvent";

export interface OcclusionInfo {
  /** The active step's resolved target element. */
  element: Element;
  /** The element sitting on top of it, when known. */
  occluder: Element | null;
  /** Analytics-safe identifier for the occluder. */
  occluderId: string;
}

/**
 * Returns occlusion info for the active step's target when it is in the DOM but
 * visually covered, else null. Subscribes to `target:occluded` (set) and
 * `target:revealed` / `target:lost` / `step:left` (clear). Mirrors
 * {@link useActiveTarget}; occlusion is a transient overlay condition kept off
 * the `TourState` machine so it doesn't ripple through every status switch.
 */
export function useTargetOcclusion(): OcclusionInfo | null {
  const engine = useTourEngine();
  const { state } = useTour();
  const [occlusion, setOcclusion] = useState<OcclusionInfo | null>(null);

  const isActiveTargetEvent = useCallback(
    (event: { tourId: string; sectionId: string; stepId: string }) => {
      const current = engine.getState();
      return (
        current.status === "step" && event.tourId === engine.config.id && event.sectionId === current.sectionId && event.stepId === current.stepId
      );
    },
    [engine]
  );

  const onOccluded = useCallback(
    (event: { tourId: string; sectionId: string; stepId: string; element: Element; occluder: Element | null; occluderId: string }) => {
      if (!isActiveTargetEvent(event)) return;
      setOcclusion({ element: event.element, occluder: event.occluder, occluderId: event.occluderId });
    },
    [isActiveTargetEvent]
  );
  const onCleared = useCallback(
    (event: { tourId: string; sectionId: string; stepId: string }) => {
      if (!isActiveTargetEvent(event)) return;
      setOcclusion(null);
    },
    [isActiveTargetEvent]
  );
  const onStepLeft = useCallback(() => setOcclusion(null), []);

  useTourEvent("target:occluded", onOccluded);
  useTourEvent("target:revealed", onCleared);
  useTourEvent("target:lost", onCleared);
  useTourEvent("step:left", onStepLeft);

  useEffect(() => {
    if (state.status !== "step") setOcclusion(null);
  }, [state]);

  return occlusion;
}
