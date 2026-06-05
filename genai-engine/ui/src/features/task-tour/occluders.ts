/**
 * Stable registry ids for tour occluder surfaces the engine reconciles closed
 * on step entry. These are registered from INSIDE `<TourProvider>` via
 * `useRegisterOccluder` (e.g. the URL-driven trace drawer in
 * `useTracesTourPrep`) — i.e. by tour code, never by presentational components.
 *
 * Most app surfaces (standard MUI modals / drawers) need NO registration at
 * all: when one covers a step's target the occlusion safety net dismisses it
 * generically via {@link import("./dismissOverlay").dismissOverlay} (Escape /
 * backdrop), so views stay fully decoupled from the tour. This registry is only
 * for the few surfaces that need precise, tour-owned close behavior a generic
 * gesture can't provide (e.g. clearing URL state).
 */
export const TASK_TOUR_OCCLUDERS = {
  traceDrawer: "task-tour.occluder.traceDrawer",
} as const;

export type TaskTourOccluderId = (typeof TASK_TOUR_OCCLUDERS)[keyof typeof TASK_TOUR_OCCLUDERS];
