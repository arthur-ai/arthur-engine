/**
 * Dispatch a `document`-level CustomEvent that the tour engine's `event`
 * triggers listen for. The event name is whatever the step's `advanceOn`
 * trigger declares; the engine attaches a `document.addEventListener` on the
 * named event when the step is active and detaches it on step exit.
 *
 * Using `document` (not `window`) matches the engine's default `event` trigger
 * implementation (see `features/tour/core/triggers/event.ts`).
 */
export function dispatchTourEvent(name: string): void {
  document.dispatchEvent(new CustomEvent(name));
}

export { TASK_TOUR_EVENTS, TASK_TOUR_TARGET_LOST_HINTS, type TaskTourEventName } from "./tourEventNames";
