import mitt from "mitt";

import type { TourBus, TourEvents } from "./types";

export function createTourBus(): TourBus {
  return mitt<TourEvents>();
}
