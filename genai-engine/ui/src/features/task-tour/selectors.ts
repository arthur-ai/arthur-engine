/**
 * Single source of truth for every `data-tour-id` the task tour points at.
 *
 * Real app components in `genai-engine/ui/src/components/**` annotate their
 * elements with `data-tour-id={TOUR_IDS.xxx}`, and the tour config in
 * `tour-config.ts` builds CSS selectors against the same values. Keeping the
 * mapping centralized here means a selector rename only ever touches one file.
 */
export const TOUR_IDS = {
  navDemoAgent: "task-tour-nav-demo-agent",
  navObserve: "task-tour-nav-observe",
  navTest: "task-tour-nav-test",
  navEvaluate: "task-tour-nav-evaluate",
  navDatasets: "task-tour-nav-datasets",
  navPrompts: "task-tour-nav-prompts",
  tracesFirstRow: "task-tour-traces-first-row",
  traceDrawerSpans: "task-tour-trace-spans",
  traceDrawerEvals: "task-tour-trace-evals",
  traceAnnotationsModal: "task-tour-trace-annotations-modal",
  traceDrawerFeedback: "task-tour-trace-feedback",
  traceFeedbackPopover: "task-tour-trace-feedback-popover",
  /**
   * Coarse wrapper around the trace drawer body for the "Add trace to dataset"
   * step. The Add-to-Dataset button itself lives inside
   * `@arthur/shared-components` so we can't add a `data-tour-id` directly on
   * it; the step is `event-only` and uses this wrapper as the visual anchor.
   */
  traceDrawerAddToDataset: "task-tour-trace-add-to-dataset",
  evaluatorsFirstCard: "task-tour-evaluator-first",
  testNotebookCreate: "task-tour-test-notebook-create",
  chatSendPlaceholder: "task-tour-chat-send",
  datasetsEntry: "task-tour-datasets-entry",
  /** First row in the datasets list — used for "open the pre-loaded dataset". */
  datasetsFirstRow: "task-tour-datasets-first-row",
  /** Generate-synthetic-data button on the dataset detail header. */
  datasetGenerateSynthetic: "task-tour-dataset-generate-synthetic",
  /** Generate-synthetic-data modal surface after the header trigger opens it. */
  datasetGenerateSyntheticModal: "task-tour-dataset-generate-synthetic-modal",
  promptsEntry: "task-tour-prompts-entry",
  /** Prompts management tab in PromptsView — used for "open the Prompts tab". */
  promptsManagementTab: "task-tour-prompts-management-tab",
  /** First row in the prompts management table — used for "inspect a prompt". */
  promptsFirstRow: "task-tour-prompts-first-row",
  /** Add-tag icon-button on the prompt detail view — used for "tag as production". */
  promptAddTag: "task-tour-prompt-add-tag",
  /** "Add Prompt" button in the playground header — used for the prompt-tuning step. */
  playgroundAddPrompt: "task-tour-playground-add-prompt",
  /** "Experiment" button in the prompts view (visible on the Runs tab). */
  promptsExperimentButton: "task-tour-prompts-experiment",
} as const;

export type TourId = (typeof TOUR_IDS)[keyof typeof TOUR_IDS];

/** Build a `[data-tour-id="..."]` selector for use in `TargetSpec`. */
export function tourSelector(id: TourId) {
  return `[data-tour-id="${id}"]` as const;
}
