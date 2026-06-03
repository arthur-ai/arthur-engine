import { useCallback } from "react";

import { useTourEngine } from "./useTour";

/**
 * Returns a typed function that emits an action onto the tour's mitt bus.
 * The `action` trigger listens for matching names and advances the active
 * step. Replaces v0's `dispatchTourEvent(name)` (which used global
 * `document.dispatchEvent` round-trips).
 *
 * ```ts
 * const emit = useTourAction();
 * emit("trace-opened");
 * ```
 */
export function useTourAction(): (name: string) => void {
  const engine = useTourEngine();
  return useCallback((name: string) => engine.emitAction(name), [engine]);
}
