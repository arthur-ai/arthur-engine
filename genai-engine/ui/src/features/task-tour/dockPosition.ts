/**
 * Shared resting position for the tour's two interchangeable "continue the
 * tour" surfaces — the resume FAB and the checklist panel (collapsed or
 * expanded). They are never both free-floating at once (the panel docks to
 * the FAB when both are shown), so a single persisted `{ left, bottom }`
 * anchor is enough to keep them grouped: whichever one the user drags writes
 * the shared position, and the other adopts it the next time it mounts.
 *
 * Positions are left-aligned — both surfaces share the same `left`/`bottom`
 * origin so their bottom-left corners line up regardless of width.
 */

/** Width of the checklist panel — the wider surface, used as the shared horizontal anchor. */
export const TASK_TOUR_DOCK_WIDTH = 320;

/** Single `localStorage` key shared by the FAB and the checklist. */
export const TASK_TOUR_DOCK_STORAGE_KEY = "task-tour:dock-position";

/** Default resting spot when nothing is stored: bottom-right, mirroring the panel's historical home. */
export function defaultDockPosition() {
  if (typeof window === "undefined") {
    return { left: 20, bottom: 20 };
  }
  return { left: Math.max(20, window.innerWidth - TASK_TOUR_DOCK_WIDTH - 20), bottom: 20 };
}
