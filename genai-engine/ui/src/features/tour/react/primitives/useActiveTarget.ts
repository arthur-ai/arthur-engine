import { useCallback, useEffect, useState } from "react";

import { useTour, useTourEngine } from "../useTour";
import { useTourEvent } from "../useTourEvent";

/**
 * Returns the current step's resolved DOM Element (or null). Subscribes to
 * `target:found` / `target:lost` / `step:left` events so React stays in sync
 * with async target resolution and clears between steps.
 */
export function useActiveTarget(): Element | null {
  const engine = useTourEngine();
  const { state } = useTour();
  const [element, setElement] = useState<Element | null>(null);

  const isActiveTargetEvent = useCallback(
    (event: { tourId: string; sectionId: string; stepId: string }) => {
      const current = engine.getState();
      return (
        current.status === "step" && event.tourId === engine.config.id && event.sectionId === current.sectionId && event.stepId === current.stepId
      );
    },
    [engine]
  );

  const onFound = useCallback(
    (event: { tourId: string; sectionId: string; stepId: string; element: Element }) => {
      if (!isActiveTargetEvent(event)) return;
      setElement(event.element);
    },
    [isActiveTargetEvent]
  );
  const onLost = useCallback(
    (event: { tourId: string; sectionId: string; stepId: string }) => {
      if (!isActiveTargetEvent(event)) return;
      setElement(null);
    },
    [isActiveTargetEvent]
  );
  const onStepLeft = useCallback(() => setElement(null), []);

  useTourEvent("target:found", onFound);
  useTourEvent("target:lost", onLost);
  useTourEvent("step:left", onStepLeft);

  useEffect(() => {
    if (state.status !== "step") {
      setElement(null);
    }
  }, [state]);

  return element;
}
