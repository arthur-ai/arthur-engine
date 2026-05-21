import { useEffect } from "react";

import type { TourEvents } from "../core/types";

import { useTourEngine } from "./useTour";

/**
 * Subscribe to a typed tour bus event. The handler is wrapped in a ref-like
 * effect, so callers don't need to memoize it.
 */
export function useTourEvent<K extends keyof TourEvents>(name: K, handler: (event: TourEvents[K]) => void): void {
  const engine = useTourEngine();
  useEffect(() => {
    engine.on(name, handler);
    return () => engine.off(name, handler);
  }, [engine, name, handler]);
}
