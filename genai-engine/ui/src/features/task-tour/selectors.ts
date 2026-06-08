import type { HTMLAttributes } from "react";

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
  /** "View full details" maximize button on the first evaluator card. */
  evaluatorMaximize: "task-tour-evaluator-maximize",
  /** Version drawer on the evaluator full-screen detail view. */
  evaluatorDetailVersions: "task-tour-evaluator-detail-versions",
  /** Instructions panel on the evaluator full-screen detail view. */
  evaluatorDetailInstructions: "task-tour-evaluator-detail-instructions",
  /** Judge-model field on the evaluator full-screen detail view. */
  evaluatorDetailModel: "task-tour-evaluator-detail-model",
  testNotebookCreate: "task-tour-test-notebook-create",
  /** Full chat panel surface for Demo Agent mini-tour pauses. */
  chatWindow: "task-tour-chat-window",
  chatSendPlaceholder: "task-tour-chat-send",
  datasetsEntry: "task-tour-datasets-entry",
  /** First row in the datasets list — used for "open the pre-loaded dataset". */
  datasetsFirstRow: "task-tour-datasets-first-row",
  /** Generate-synthetic-data button on the dataset detail header. */
  datasetGenerateSynthetic: "task-tour-dataset-generate-synthetic",
  /** Generate-synthetic-data modal surface after the header trigger opens it. */
  datasetGenerateSyntheticModal: "task-tour-dataset-generate-synthetic-modal",
  /** Row table on the dataset detail view — "each row is a test case". */
  datasetTable: "task-tour-dataset-table",
  /** Configure-columns button on the dataset detail header. */
  datasetConfigureColumns: "task-tour-dataset-configure-columns",
  /** Configure-columns modal surface after the header trigger opens it. */
  datasetConfigureColumnsModal: "task-tour-dataset-configure-columns-modal",
  /** Import / Generate / Add Row button group on the dataset detail header. */
  datasetDataActions: "task-tour-dataset-data-actions",
  /** Versions button on the dataset detail header. */
  datasetVersions: "task-tour-dataset-versions",
  /** Experiments button on the dataset detail header. */
  datasetExperiments: "task-tour-dataset-experiments",
  promptsEntry: "task-tour-prompts-entry",
  /** Prompts management tab in PromptsView — used for "open the Prompts tab". */
  promptsManagementTab: "task-tour-prompts-management-tab",
  /** Demo prompt row in the prompts management table — used for "inspect a prompt". */
  promptsFirstRow: "task-tour-prompts-first-row",
  /** Prompt detail button that opens the selected prompt in the playground. */
  promptOpenInPlayground: "task-tour-prompt-open-in-playground",
  /** Add-tag icon-button on the prompt detail view — used for "tag as production". */
  promptAddTag: "task-tour-prompt-add-tag",
  /** Prompt tags popover opened by the add-tag icon button. */
  promptTagsPopover: "task-tour-prompt-tags-popover",
  /** Duplicate Prompt icon-button on the first playground prompt card. */
  playgroundDuplicatePrompt: "task-tour-playground-duplicate-prompt",
  /** "Add Prompt" button in the playground header — used after duplicating the seeded prompt. */
  playgroundAddPrompt: "task-tour-playground-add-prompt",
  /** Newest prompt card in the playground prompt column list. */
  playgroundPromptCard: "task-tour-playground-prompt-card",
  /** Variables control in the playground header. */
  playgroundVariablesButton: "task-tour-playground-variables",
  /** Opened Variables panel surface (Base UI popover) in the playground header. */
  playgroundVariablesPanel: "task-tour-playground-variables-panel",
  /** Save icon-button on a playground prompt card — used to nudge saving a new prompt version. */
  playgroundSavePrompt: "task-tour-playground-save-prompt",
  /** Root panel of the prompts playground — used for the full-notebook wrap-up step. */
  playgroundPanel: "task-tour-playground-panel",
  /** "Experiment" button in the prompts view (visible on the Runs tab). */
  promptsExperimentButton: "task-tour-prompts-experiment",
  /** Create New item in the Prompt Runs Experiment menu. */
  promptsExperimentCreateNew: "task-tour-prompts-experiment-create-new",
  /** Create Experiment dialog surface after the Prompt Runs Experiment menu opens it. */
  createExperimentModal: "task-tour-create-experiment-modal",
  /** Experiment Info section inside the Create Experiment dialog. */
  createExperimentInfoStep: "task-tour-create-experiment-info",
  /** Name + Description fields inside the Experiment Info step. */
  createExperimentInfoName: "task-tour-create-experiment-info-name",
  /** Prompt Versions block inside the Experiment Info step. */
  createExperimentInfoVersions: "task-tour-create-experiment-info-versions",
  /** Dataset block inside the Experiment Info step. */
  createExperimentInfoDataset: "task-tour-create-experiment-info-dataset",
  /** Evaluators block inside the Experiment Info step. */
  createExperimentInfoEvaluators: "task-tour-create-experiment-info-evaluators",
  /** Configure Prompts section inside the Create Experiment dialog. */
  createExperimentPromptMappingsStep: "task-tour-create-experiment-prompt-mappings",
  /** Prompt-variable mapping list inside the Configure Prompts step. */
  createExperimentPromptMappingsList: "task-tour-create-experiment-prompt-mappings-list",
  /** Configure Evals section inside the Create Experiment dialog. */
  createExperimentEvalMappingsStep: "task-tour-create-experiment-eval-mappings",
  /** Eval-variable mapping list inside the Configure Evals step. */
  createExperimentEvalMappingsList: "task-tour-create-experiment-eval-mappings-list",
  /** Final Create Experiment action in the dialog. */
  createExperimentSubmit: "task-tour-create-experiment-submit",
} as const;

export type TourId = (typeof TOUR_IDS)[keyof typeof TOUR_IDS];

/** Build a `[data-tour-id="..."]` selector for use in `TargetSpec`. */
export function tourSelector(id: TourId) {
  return `[data-tour-id="${id}"]` as const;
}

/**
 * `data-tour-id` props for a portaled MUI surface (`slotProps.paper` / `root`).
 * Centralizes the `as HTMLAttributes<HTMLDivElement>` cast that `data-*` keys
 * require (they aren't in MUI's typed slot props) — a wrong slot/element
 * generic otherwise compiles but silently fails to anchor at runtime. Spread
 * alongside any other paper props: `paper: { ...tourDataAttr(id), sx }`.
 */
export function tourDataAttr(id: TourId): HTMLAttributes<HTMLDivElement> {
  return { "data-tour-id": id } as HTMLAttributes<HTMLDivElement>;
}
