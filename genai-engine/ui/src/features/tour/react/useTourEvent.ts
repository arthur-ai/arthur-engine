import { useEffect } from "react";

import type { TourEvents } from "../core/types";

import { useTourEngine } from "./useTour";

/**
 * Subscribe to a typed tour bus event. The handler should be stable
 * (memoized via useCallback) — if it isn't, the effect resubscribes on
 * every render, which is wasteful but not incorrect.
 */
export function useTourEvent<K extends keyof TourEvents>(name: K, handler: (event: TourEvents[K]) => void): void {
  const engine = useTourEngine();
  useEffect(() => {
    engine.on(name, handler);
    return () => engine.off(name, handler);
  }, [engine, name, handler]);
}
