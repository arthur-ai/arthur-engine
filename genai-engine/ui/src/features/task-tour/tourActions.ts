/**
 * Typed action channel for the task tour. v1 replaces v0's untyped
 * `document.dispatchEvent(new CustomEvent(name))` pattern with a typed action
 * name dispatched onto the engine's mitt bus via `engine.emitAction(name)`.
 *
 * Two surfaces are exposed:
 *  - `TASK_TOUR_ACTIONS` and the `TaskTourAction` union — preferred entry
 *    point for new code. Use `useTourAction()(TASK_TOUR_ACTIONS.xxx)` from
 *    inside a `<TourProvider>` subtree.
 *  - `TASK_TOUR_EVENTS` and `dispatchTourEvent(name)` — kept as backward-
 *    compatible aliases for product code authored against v0. They emit onto
 *    the active engine's bus via {@link registerTaskTourActionBridge}, so the
 *    call sites don't have to change.
 *
 * The bridge is initialised inside `TaskTour` once the engine is created and
 * torn down when the tour unmounts. If `dispatchTourEvent` is called outside
 * a tour lifecycle the call is a no-op rather than throwing — matches v0's
 * "fire and forget" semantics (where the engine just wasn't listening yet).
 */
export const TASK_TOUR_ACTIONS = {
  evaluateOpened: "task-tour:evaluate-opened",
  evaluatorReviewed: "task-tour:evaluator-reviewed",
  observeOpened: "task-tour:observe-opened",
  traceOpened: "task-tour:trace-opened",
  spansReviewed: "task-tour:spans-reviewed",
  annotationsReviewed: "task-tour:annotations-reviewed",
  feedbackAdded: "task-tour:feedback-added",
  datasetsOpened: "task-tour:datasets-opened",
  datasetOpened: "task-tour:dataset-opened",
  traceAddedToDataset: "task-tour:trace-added-to-dataset",
  datasetRowVerified: "task-tour:dataset-row-verified",
  syntheticDataGenerated: "task-tour:synthetic-data-generated",
  promptsOpened: "task-tour:prompts-opened",
  promptsManagementTabOpened: "task-tour:prompts-management-tab-opened",
  promptInspected: "task-tour:prompt-inspected",
  playgroundPromptsCreated: "task-tour:playground-prompts-created",
  experimentRun: "task-tour:experiment-run",
  promptPromoted: "task-tour:prompt-promoted",
  deployVerified: "task-tour:deploy-verified",
} as const;

export type TaskTourAction = (typeof TASK_TOUR_ACTIONS)[keyof typeof TASK_TOUR_ACTIONS];

/**
 * Kept as a name-compatible alias of {@link TASK_TOUR_ACTIONS} so v0 call
 * sites continue compiling without modification.
 *
 * @deprecated Use {@link TASK_TOUR_ACTIONS} in new code.
 */
export const TASK_TOUR_EVENTS = TASK_TOUR_ACTIONS;
export type TaskTourEventName = TaskTourAction;

type Bridge = (name: string) => void;

let activeBridge: Bridge | null = null;

/**
 * Called by `TaskTour` once the engine is mounted to wire
 * {@link dispatchTourEvent} to the engine's action bus. Returns a teardown
 * function that restores the previous bridge (typically null) so nested or
 * remounted tours don't leak the reference.
 */
export function registerTaskTourActionBridge(bridge: Bridge | null): () => void {
  const previous = activeBridge;
  activeBridge = bridge;
  return () => {
    activeBridge = previous;
  };
}

/**
 * v1 wrapper that emits `name` onto the active tour engine's mitt bus.
 *
 * Backward-compatible drop-in for v0's `document.dispatchEvent(new
 * CustomEvent(name))`. The product code keeps calling
 * `dispatchTourEvent(TASK_TOUR_EVENTS.xxx)` unchanged — the only difference is
 * the dispatch now routes through `engine.emitAction(name)` (clearly typed,
 * scoped to the active tour, observable by analytics plugins).
 *
 * No-op when no tour is mounted, matching v0's silent-when-idle behaviour.
 */
export function dispatchTourEvent(name: string): void {
  activeBridge?.(name);
}

/** Keys are `${sectionId}.${stepId}` — shown under the active checklist row when the spotlight target is missing. */
export const TASK_TOUR_TARGET_LOST_HINTS: Partial<Record<string, string>> = {
  "traces.open-trace": "Click a trace row, or mark this step complete to open the top trace automatically.",
  "traces.review-spans": "Open a trace first — the highlight appears once the drawer is visible.",
  "traces.review-annotations": "Open a trace and scroll to the eval annotations to continue.",
  "traces.add-feedback": "Open a trace, then submit manual feedback to continue.",
  "datasets.add-trace-to-dataset": "Open a trace and use Add to Dataset to capture it as a test case.",
  "datasets.verify-new-row": "Return to Datasets and open the dataset to confirm the new row landed.",
  "prompts.open-prompts-tab": "Open Prompt in the sidebar first, then click the Prompts tab.",
  "prompts.create-prompts-in-playground": "Open a notebook from the Notebooks tab, then use Add Prompt in the playground.",
  "deploy.tag-production": "Open a prompt detail view and tag the winning version as production.",
  "deploy.verify-eval-passes": "Open Observe and inspect a fresh trace to confirm the eval passes.",
};
