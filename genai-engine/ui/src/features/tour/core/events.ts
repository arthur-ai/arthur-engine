import mitt from "mitt";

import type { TourBus, TourEvents } from "./types";

export const TOUR_EVENT_NAMES = [
  "tour:start",
  "tour:end",
  "section:enter",
  "section:exit",
  "section:skip",
  "section:introduction:show",
  "section:introduction:acknowledge",
  "step:before-enter",
  "step:enter",
  "step:exit",
  "step:advance",
  "target:found",
  "target:lost",
  "navigation:before",
  "navigation:after",
] as const satisfies ReadonlyArray<keyof TourEvents>;

export type TourEventName = (typeof TOUR_EVENT_NAMES)[number];

export function createTourBus(): TourBus {
  return mitt<TourEvents>();
}
