/**
 * Typed action channel for the task tour. Product code dispatches a typed
 * action name that the active engine advances on via `engine.emitAction(name)`.
 *
 * Two surfaces are exposed:
 *  - `dispatchTourEvent(name)` + `TASK_TOUR_EVENTS` — the canonical product
 *    entry point. Most dispatching components (sidebar, chat, trace drawer,
 *    feedback popover, …) render OUTSIDE `<TourProvider>`, so they cannot use
 *    the `useTourAction()` hook (it throws without the provider). The
 *    `dispatchTourEvent` global bridge exists precisely for them: it forwards
 *    onto the active engine's bus via {@link registerTaskTourActionBridge}.
 *  - `useTourAction()(TASK_TOUR_ACTIONS.xxx)` — the in-provider equivalent for
 *    widgets that already live under `<TourProvider>`. Same underlying bus.
 *
 * The bridge is initialised inside `TaskTour` once the engine is created and
 * torn down when the tour unmounts. If `dispatchTourEvent` is called outside
 * a tour lifecycle the call is a no-op rather than throwing (the engine simply
 * isn't listening yet).
 */
export const TASK_TOUR_ACTIONS = {
  demoAgentOpened: "task-tour:demo-agent-opened",
  demoAgentMessageSent: "task-tour:demo-agent-message-sent",
  evaluateOpened: "task-tour:evaluate-opened",
  evaluatorMaximized: "task-tour:evaluator-maximized",
  evaluateResultsOpened: "task-tour:evaluate-results-opened",
  evaluateResultDetailsReviewed: "task-tour:evaluate-result-details-reviewed",
  observeOpened: "task-tour:observe-opened",
  traceOpened: "task-tour:trace-opened",
  spansReviewed: "task-tour:spans-reviewed",
  annotationsReviewed: "task-tour:annotations-reviewed",
  feedbackAdded: "task-tour:feedback-added",
  datasetsOpened: "task-tour:datasets-opened",
  datasetOpened: "task-tour:dataset-opened",
  traceAddToDatasetOpened: "task-tour:trace-add-to-dataset-opened",
  traceAddedToDataset: "task-tour:trace-added-to-dataset",
  datasetRowVerified: "task-tour:dataset-row-verified",
  syntheticDataFinished: "task-tour:synthetic-data-finished",
  promptsOpened: "task-tour:prompts-opened",
  promptsManagementTabOpened: "task-tour:prompts-management-tab-opened",
  promptInspected: "task-tour:prompt-inspected",
  promptOpenedInPlayground: "task-tour:prompt-opened-in-playground",
  playgroundPromptsCreated: "task-tour:playground-prompts-created",
  /** Emitted when the playground Variables panel is closed — advances the review-variables beat. */
  playgroundVariablesReviewed: "task-tour:playground-variables-reviewed",
  createExperimentModalOpened: "task-tour:create-experiment-modal-opened",
  createExperimentInfoCompleted: "task-tour:create-experiment-info-completed",
  createExperimentPromptMappingsCompleted: "task-tour:create-experiment-prompt-mappings-completed",
  createExperimentCreated: "task-tour:create-experiment-created",
  promptPromoted: "task-tour:prompt-promoted",
  deployVerified: "task-tour:deploy-verified",
} as const;

export type TaskTourAction = (typeof TASK_TOUR_ACTIONS)[keyof typeof TASK_TOUR_ACTIONS];

/**
 * Name-compatible alias of {@link TASK_TOUR_ACTIONS}. `TASK_TOUR_EVENTS` is the
 * label product code imports when dispatching via {@link dispatchTourEvent};
 * both point at the same typed action names.
 */
export const TASK_TOUR_EVENTS = TASK_TOUR_ACTIONS;
export type TaskTourEventName = TaskTourAction;

type Bridge = (name: TaskTourAction) => void;

let activeBridge: Bridge | null = null;
let activeTargetRefreshBridge: (() => void) | null = null;

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

export function registerTaskTourTargetRefreshBridge(bridge: (() => void) | null): () => void {
  const previous = activeTargetRefreshBridge;
  activeTargetRefreshBridge = bridge;
  return () => {
    activeTargetRefreshBridge = previous;
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
export function dispatchTourEvent(name: TaskTourAction): void {
  activeBridge?.(name);
}

export function refreshTaskTourTarget(): void {
  activeTargetRefreshBridge?.();
}

/** Keys are `${sectionId}.${stepId}` — shown under the active checklist row when the spotlight target is missing. */
export const TASK_TOUR_TARGET_LOST_HINTS: Partial<Record<string, string>> = {
  "traces.open-trace": "Click a trace row, or mark this step complete to open the top trace automatically.",
  "traces.review-spans": "Open a trace first — the highlight appears once the drawer is visible.",
  "traces.review-annotations": "Open a trace and scroll to the eval annotations to continue.",
  "traces.add-feedback": "Open a trace, then submit manual feedback to continue.",
  "evals.review-evaluator": "Open Evaluate, then use the maximize icon on the first evaluator to see its full details.",
  "evals.review-evaluator-versions": "Open an evaluator's full details — the version history appears in the left drawer.",
  "evals.review-evaluator-instructions": "Open an evaluator's full details to read the instructions sent to the judge model.",
  "evals.review-evaluator-model": "Open an evaluator's full details to see which model judges each trace.",
  "evals.open-results-tab": "Open Evaluate, then click the Results tab to inspect eval outcomes.",
  "evals.review-result-details": "Open the Results tab and click the first result row to review its details.",
  "datasets.open-traces-for-dataset": "Open Observe so you can capture the failing trace.",
  "datasets.open-trace-for-dataset": "Click the failing trace row before adding it to the dataset.",
  "datasets.review-trace-actions": "Open a trace first — Trace Actions appears in the trace drawer.",
  "datasets.open-add-to-dataset": "Use Trace Actions to open Add to Dataset.",
  "datasets.save-trace-to-dataset": "Save the Add-to-Dataset drawer to capture the trace as a test case.",
  "datasets.verify-new-row": "Return to Datasets and open the dataset to confirm the new row landed.",
  "datasets.generate-synthetic": "Open the dataset detail page, then use Generate or skip this optional step.",
  "prompts.open-prompts-tab": "Open Prompt in the sidebar first, then click the Prompts tab.",
  "prompts.inspect-prompt": "Open the Prompts tab, then click the highlighted prompt row.",
  "prompts.open-in-playground": "Open a prompt detail view, then click Open in Playground.",
  "prompts.duplicate-prompt-in-playground": "Use Duplicate Prompt in the playground to copy the seeded prompt first.",
  "prompts.review-playground-prompt": "Duplicate a prompt first — the highlight moves to the newest prompt card once it appears.",
  "prompts.open-variables": "Click Variables in the playground header to open the variables panel.",
  "prompts.review-playground-controls": "Open the Variables panel, review the variable values, then close it to continue.",
  "deploy.open-production-prompt": "Open the Prompts tab, then click the prompt you want to promote.",
  "deploy.tag-production": "Open a prompt detail view and tag the winning version as production.",
  "deploy.reopen-demo-agent": "Open the Demo Agent so you can generate a fresh trace with the production prompt.",
  "deploy.send-verification-message": "Send another Demo Agent message to create a fresh trace before checking evals.",
  "deploy.review-verification-message": "Stay on the Demo Agent until the fresh response finishes, then continue.",
  "deploy.verify-eval-passes": "Open Observe and inspect a fresh trace to confirm the eval passes.",
};

export interface OcclusionHint {
  message: string;
  actionLabel: string;
}

/**
 * Optional per-step occlusion copy (keyed `${sectionId}.${stepId}`), shown with
 * an actionable button under the active checklist row when the spotlight target
 * is in the DOM but covered by another surface. Falls back to
 * {@link DEFAULT_OCCLUSION_HINT}.
 */
export const TASK_TOUR_OCCLUSION_HINTS: Partial<Record<string, OcclusionHint>> = {};

export const DEFAULT_OCCLUSION_HINT: OcclusionHint = {
  message: "Something is covering this step. We can bring it back into view.",
  actionLabel: "Bring this into view",
};
