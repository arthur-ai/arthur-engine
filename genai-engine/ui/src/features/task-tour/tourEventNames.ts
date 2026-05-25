/**
 * Canonical custom-event names the tour engine listens for on `document`.
 * Keep in sync with [content/wiring.ts](./content/wiring.ts) — wiring imports
 * these constants so renames stay single-source.
 */
export const TASK_TOUR_EVENTS = {
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
  promptInspected: "task-tour:prompt-inspected",
  playgroundPromptsCreated: "task-tour:playground-prompts-created",
  experimentRun: "task-tour:experiment-run",
  promptPromoted: "task-tour:prompt-promoted",
  deployVerified: "task-tour:deploy-verified",
} as const;

export type TaskTourEventName = (typeof TASK_TOUR_EVENTS)[keyof typeof TASK_TOUR_EVENTS];

/** Keys are `${sectionId}.${stepId}` — shown under the active checklist row when the spotlight target is missing. */
export const TASK_TOUR_TARGET_LOST_HINTS: Partial<Record<string, string>> = {
  "traces.open-trace": "Click a trace row in the table to continue.",
  "traces.review-spans": "Open a trace first — the highlight appears once the drawer is visible.",
  "traces.review-annotations": "Open a trace and scroll to the eval annotations to continue.",
  "traces.add-feedback": "Open a trace, then submit manual feedback to continue.",
  "datasets.add-trace-to-dataset": "Open a trace and use Add to Dataset to capture it as a test case.",
  "datasets.verify-new-row": "Return to Datasets and open the dataset to confirm the new row landed.",
  "prompts.create-prompts-in-playground": "Open a notebook from the Notebooks tab, then use Add Prompt in the playground.",
  "deploy.tag-production": "Open a prompt detail view and tag the winning version as production.",
  "deploy.verify-eval-passes": "Open Observe and inspect a fresh trace to confirm the eval passes.",
};
