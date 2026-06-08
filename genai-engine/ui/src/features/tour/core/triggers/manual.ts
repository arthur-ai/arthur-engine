import type { TriggerFactory } from "../types";

/**
 * Manual triggers have no DOM hookup — `tour.next()` is the only way to
 * advance.
 */
export const manualTrigger: TriggerFactory = () => {
  return () => {};
};
