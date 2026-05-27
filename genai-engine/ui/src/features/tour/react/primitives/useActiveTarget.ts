import { useCallback, useEffect, useState } from "react";

import { useTour } from "../useTour";
import { useTourEvent } from "../useTourEvent";

/**
 * Returns the current step's resolved DOM Element (or null). Subscribes to
 * `target:found` / `target:lost` / `step:left` events so React stays in sync
 * with async target resolution and clears between steps.
 */
export function useActiveTarget(): Element | null {
  const { state } = useTour();
  const [element, setElement] = useState<Element | null>(null);

  const onFound = useCallback((event: { stepId: string; element: Element }) => {
    setElement(event.element);
  }, []);
  const onLost = useCallback(() => setElement(null), []);
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
