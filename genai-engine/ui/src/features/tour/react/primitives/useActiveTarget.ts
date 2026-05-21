import { useCallback, useEffect, useState } from "react";

import { useTour } from "../useTour";
import { useTourEvent } from "../useTourEvent";

/**
 * Returns the current step's resolved DOM Element (or null). Subscribes to
 * `target:found` / `target:lost` / `step:exit` events from the engine so React
 * stays in sync with async target resolution and clears between steps to avoid
 * a stale highlight during navigation.
 */
export function useActiveTarget(): Element | null {
  const { state } = useTour();
  const [element, setElement] = useState<Element | null>(null);

  const onFound = useCallback((event: { stepId: string; element: Element }) => {
    setElement(event.element);
  }, []);
  const onLost = useCallback(() => {
    setElement(null);
  }, []);
  const onStepExit = useCallback(() => {
    setElement(null);
  }, []);

  useTourEvent("target:found", onFound);
  useTourEvent("target:lost", onLost);
  useTourEvent("step:exit", onStepExit);

  useEffect(() => {
    if (state.status !== "running" || state.introductionPending) {
      setElement(null);
    }
  }, [state]);

  return element;
}
