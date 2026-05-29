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
  /** Results tab on the Evaluate page. */
  evaluateResultsTab: "task-tour-evaluate-results-tab",
  /** First row in Evaluate > Results. */
  evaluateResultsFirstRow: "task-tour-evaluate-results-first-row",
  /** Details dialog opened from an Evaluate results row. */
  evaluateResultsDetailsDialog: "task-tour-evaluate-results-details-dialog",
  tracesFirstRow: "task-tour-traces-first-row",
  traceDrawerSpans: "task-tour-trace-spans",
  traceDrawerEvals: "task-tour-trace-evals",
  traceAnnotationsModal: "task-tour-trace-annotations-modal",
  traceDrawerFeedback: "task-tour-trace-feedback",
  traceFeedbackPopover: "task-tour-trace-feedback-popover",
  /** Trace drawer actions region containing secondary trace actions. */
  traceActions: "task-tour-trace-actions",
  /**
   * Coarse wrapper around the trace drawer body for the "Add trace to dataset"
   * step. The Add-to-Dataset button itself lives inside
   * `@arthur/shared-components` so we can't add a `data-tour-id` directly on
   * it; the step is `event-only` and uses this wrapper as the visual anchor.
   */
  traceDrawerAddToDataset: "task-tour-trace-add-to-dataset",
  /** Trace drawer Add-to-Dataset action control when discoverable in the DOM. */
  traceAddToDatasetAction: "task-tour-trace-add-to-dataset-action",
  /** Add-to-Dataset drawer surface after the trace drawer trigger opens it. */
  traceAddToDatasetDrawer: "task-tour-trace-add-to-dataset-drawer",
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
  /** Prompt detail button that opens the selected prompt in the playground. */
  promptOpenInPlayground: "task-tour-prompt-open-in-playground",
  /** Add-tag icon-button on the prompt detail view — used for "tag as production". */
  promptAddTag: "task-tour-prompt-add-tag",
  /** Prompt tags popover opened by the add-tag icon button. */
  promptTagsPopover: "task-tour-prompt-tags-popover",
  /** "Add Prompt" button in the playground header — used for the prompt-tuning step. */
  playgroundAddPrompt: "task-tour-playground-add-prompt",
  /** Newest prompt card in the playground prompt column list. */
  playgroundPromptCard: "task-tour-playground-prompt-card",
  /** Variables control in the playground header. */
  playgroundVariablesButton: "task-tour-playground-variables",
  /** "Experiment" button in the prompts view (visible on the Runs tab). */
  promptsExperimentButton: "task-tour-prompts-experiment",
  /** Create New item in the Prompt Runs Experiment menu. */
  promptsExperimentCreateNew: "task-tour-prompts-experiment-create-new",
  /** Create Experiment dialog surface after the Prompt Runs Experiment menu opens it. */
  createExperimentModal: "task-tour-create-experiment-modal",
  /** Experiment Info section inside the Create Experiment dialog. */
  createExperimentInfoStep: "task-tour-create-experiment-info",
  /** Configure Prompts section inside the Create Experiment dialog. */
  createExperimentPromptMappingsStep: "task-tour-create-experiment-prompt-mappings",
  /** Configure Evals section inside the Create Experiment dialog. */
  createExperimentEvalMappingsStep: "task-tour-create-experiment-eval-mappings",
  /** Final Create Experiment action in the dialog. */
  createExperimentSubmit: "task-tour-create-experiment-submit",
} as const;

export type TourId = (typeof TOUR_IDS)[keyof typeof TOUR_IDS];

/** Build a `[data-tour-id="..."]` selector for use in `TargetSpec`. */
export function tourSelector(id: TourId) {
  return `[data-tour-id="${id}"]` as const;
}
