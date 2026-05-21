import type { TriggerFactory } from "../types";

/**
 * Manual triggers are advanced by the user calling tour.next() / tour.skip() /
 * pressing a button. They have no DOM hookup; the factory just returns a no-op
 * detach function.
 */
export const manualTrigger: TriggerFactory = () => {
  return () => {
    // no-op
  };
};
