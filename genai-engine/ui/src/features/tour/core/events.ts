import mitt from "mitt";

import type { TourBus, TourEvents } from "./types";

export const TOUR_EVENT_NAMES = [
  "tour:start",
  "tour:end",
  "tour:dismiss",
  "tour:resume",
  "section:enter",
  "section:exit",
  "section:skip",
  "section:intro:show",
  "section:intro:acknowledge",
  "step:enter",
  "step:completed",
  "step:left",
  "target:found",
  "target:lost",
  "navigation:before",
  "navigation:after",
  "action:emit",
] as const satisfies ReadonlyArray<keyof TourEvents>;

export type TourEventName = (typeof TOUR_EVENT_NAMES)[number];

export function createTourBus(): TourBus {
  return mitt<TourEvents>();
}
