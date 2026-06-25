/**
 * Scoped re-exports of the typed action API. This is the CANONICAL import path
 * for product components that dispatch tour events: importing from here (rather
 * than the package barrel `@/features/task-tour`) keeps the tour engine and its
 * markdown content out of a leaf component's dependency and test graph. Pair
 * with `@/features/task-tour/selectors` for `TOUR_IDS`.
 */
export {
  dispatchTourEvent,
  refreshTaskTourTarget,
  TASK_TOUR_ACTIONS,
  TASK_TOUR_EVENTS,
  TASK_TOUR_TARGET_LOST_HINTS,
  type TaskTourAction,
  type TaskTourEventName,
} from "./tourActions";
