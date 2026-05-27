/**
 * Backward-compatible re-exports of the v1 typed action API so existing
 * call sites (which import from `@/features/task-tour/tourEvents`) keep
 * compiling unchanged. New code should import from
 * `@/features/task-tour/tourActions` directly.
 */
export {
  dispatchTourEvent,
  TASK_TOUR_ACTIONS,
  TASK_TOUR_EVENTS,
  TASK_TOUR_TARGET_LOST_HINTS,
  type TaskTourAction,
  type TaskTourEventName,
} from "./tourActions";
