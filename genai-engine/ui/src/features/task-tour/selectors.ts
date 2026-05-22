/**
 * Single source of truth for every `data-tour-id` the task tour points at.
 *
 * Real app components in `genai-engine/ui/src/components/**` annotate their
 * elements with `data-tour-id={TOUR_IDS.xxx}`, and the tour config in
 * `tour-config.ts` builds CSS selectors against the same values. Keeping the
 * mapping centralized here means a selector rename only ever touches one file.
 */
export const TOUR_IDS = {
  navObserve: "task-tour-nav-observe",
  navTest: "task-tour-nav-test",
  navEvaluate: "task-tour-nav-evaluate",
  navDatasets: "task-tour-nav-datasets",
  navPrompts: "task-tour-nav-prompts",
  tracesFirstRow: "task-tour-traces-first-row",
  traceDrawerSpans: "task-tour-trace-spans",
  traceDrawerEvals: "task-tour-trace-evals",
  traceDrawerFeedback: "task-tour-trace-feedback",
  evaluatorsFirstCard: "task-tour-evaluator-first",
  testNotebookCreate: "task-tour-test-notebook-create",
  chatSendPlaceholder: "task-tour-chat-send",
  datasetsEntry: "task-tour-datasets-entry",
  promptsEntry: "task-tour-prompts-entry",
} as const;

export type TourId = (typeof TOUR_IDS)[keyof typeof TOUR_IDS];

/** Build a `[data-tour-id="..."]` selector for use in `TargetSpec`. */
export function tourSelector(id: TourId) {
  return `[data-tour-id="${id}"]` as const;
}
