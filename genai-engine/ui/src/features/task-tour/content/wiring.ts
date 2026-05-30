import { TOUR_IDS, type TourId } from "../selectors";
import { TASK_TOUR_ACTIONS } from "../tourActions";

import type { StepFormPrefill, StepPopoverConfig } from "@/features/tour";

/**
 * Real-app sub-route under `/tasks/:taskId/`. Mirrors the keys in `App.tsx`
 * — both flat segments (`overview`) and nested ones (`playgrounds/prompts`)
 * are supported. The literal becomes the suffix of the URL pathname
 * verbatim, so add new entries here whenever a step needs to deep-link
 * into a route the existing list doesn't cover. Routes that depend on
 * runtime IDs (e.g. `datasets/:datasetId`) cannot be expressed statically;
 * those steps must rely on the user having reached the page from a prior
 * step's interaction.
 */
export type TaskSubRoute =
  | "overview"
  | "traces"
  | "test"
  | "chatbot"
  | "evaluate"
  | "datasets"
  | "prompts"
  | "prompts-management"
  | "playgrounds/prompts";

/**
 * Engineering-only wiring for one tour step. Lives next to the marketing
 * markdown so a step-id rename only touches two files (the section markdown
 * and this map). Every field except `targetId` and `eventName` is optional.
 *
 * - `targetId` — `data-tour-id` value the spotlight points at, declared in
 *   [selectors.ts](../selectors.ts). When `targetHookId` is set the engine
 *   uses a registered queryHook resolver instead of the static
 *   `[data-tour-id="..."]` selector — see the dogfood report on
 *   `tracesFirstRow` / `traceDrawerSpans`.
 * - `targetHookId` — optional queryHook ID the engine consults to resolve the
 *   target via a live React ref/hook (replaces flaky data-tour-id propagation
 *   through third-party component wrappers).
 * - `actionName` — typed action name emitted via `useTourAction()` /
 *   `engine.emitAction(...)`. v1's action trigger listens on the engine bus,
 *   not `document.dispatchEvent`.
 * - `route` — optional route the engine navigates to before resolving the
 *   target. Omit when the target lives in the persistent task shell.
 * - `search` — optional search params appended to the route.
 * - `advance` — `"click+action"` (default) attaches both triggers; use
 *   `"action-only"` for coarse / page-level placeholder targets where a click
 *   shouldn't auto-advance.
 * - `prepareKey` — optional preparation hook key the engine fires before
 *   resolving the target (e.g. open the trace drawer for trace-row steps).
 * - `skipWhenEmptyKey` — opaque key the consumer-side `skipWhen` predicate
 *   reads to auto-skip empty-state steps (e.g. no evaluators).
 */
export interface StepWiring {
  targetId: TourId;
  targetHookId?: string;
  actionName: string;
  route?: TaskSubRoute;
  search?: Record<string, string>;
  advance?: "click+action" | "action-only" | "manual";
  prepareKey?: string;
  skipWhenEmptyKey?: string;
  popover?: StepPopoverConfig;
  formPrefill?: StepFormPrefill;
}

/**
 * Per-section wiring. v1 supports intro-only sections natively — sections
 * with `steps: {}` collapse to a single intro acknowledgement and advance.
 */
export interface SectionWiring {
  steps: Record<string, StepWiring>;
}

/**
 * The complete engineering wiring for the tour. Keys are section IDs that
 * must match the `id` field in the corresponding markdown frontmatter; inner
 * step keys must match the `## step: <id>` headings in the body. The loader
 * enforces both invariants at module load.
 */
/** Stable keys used by widgets to register query-hook resolvers. */
export const TASK_TOUR_QUERY_HOOKS = {
  evaluateResultDetails: "task-tour.evaluateResultDetails",
  evaluatorDetailVersions: "task-tour.evaluatorDetailVersions",
  evaluatorDetailInstructions: "task-tour.evaluatorDetailInstructions",
  evaluatorDetailModel: "task-tour.evaluatorDetailModel",
  tracesFirstRow: "task-tour.tracesFirstRow",
  traceDrawerSpans: "task-tour.traceDrawerSpans",
  traceDrawerEvals: "task-tour.traceDrawerEvals",
  traceDrawerFeedback: "task-tour.traceDrawerFeedback",
  traceDrawerAddToDataset: "task-tour.traceDrawerAddToDataset",
  traceActions: "task-tour.traceActions",
  traceAddToDatasetAction: "task-tour.traceAddToDatasetAction",
  traceAddToDatasetDrawer: "task-tour.traceAddToDatasetDrawer",
  datasetGenerateSynthetic: "task-tour.datasetGenerateSynthetic",
  demoTaskPromptRow: "task-tour.demoTaskPromptRow",
  promptOpenInPlayground: "task-tour.promptOpenInPlayground",
  promptTags: "task-tour.promptTags",
  playgroundPromptCard: "task-tour.playgroundPromptCard",
  playgroundSavePrompt: "task-tour.playgroundSavePrompt",
  createExperimentEntry: "task-tour.createExperimentEntry",
  createExperimentInfo: "task-tour.createExperimentInfo",
  createExperimentPromptMappings: "task-tour.createExperimentPromptMappings",
  createExperimentFinal: "task-tour.createExperimentFinal",
} as const;

/** Stable keys used by widgets to register preparation hooks. */
export const TASK_TOUR_PREPARATIONS = {
  traceOpened: "task-tour.prep.traceOpened",
} as const;

/**
 * Stable opaque keys consulted by the consumer's `skipWhen` predicate for
 * empty-state auto-skipping. See dogfood report (P1: empty evaluators page).
 */
export const TASK_TOUR_SKIP_WHEN = {
  noEvaluators: "task-tour.skip.noEvaluators",
} as const;

export const TASK_TOUR_WIRING: Record<string, SectionWiring> = {
  intro: { steps: {} },
  agent: {
    steps: {
      "open-demo-agent": {
        targetId: TOUR_IDS.navDemoAgent,
        actionName: TASK_TOUR_ACTIONS.demoAgentOpened,
        route: "chatbot",
      },
      "send-message": {
        targetId: TOUR_IDS.chatSendPlaceholder,
        actionName: TASK_TOUR_ACTIONS.demoAgentMessageSent,
        route: "chatbot",
        advance: "action-only",
        formPrefill: {
          targetId: TOUR_IDS.chatSendPlaceholder,
          value: "What are AI Agent Evals?",
        },
      },
    },
  },
  evals: {
    steps: {
      "open-evaluate": {
        targetId: TOUR_IDS.navEvaluate,
        actionName: TASK_TOUR_ACTIONS.evaluateOpened,
      },
      "review-evaluator": {
        targetId: TOUR_IDS.evaluatorMaximize,
        route: "evaluate",
        actionName: TASK_TOUR_ACTIONS.evaluatorMaximized,
        advance: "action-only",
        skipWhenEmptyKey: TASK_TOUR_SKIP_WHEN.noEvaluators,
      },
      // The maximize click navigates to the dynamic evaluator-detail URL
      // (/tasks/:taskId/evaluators/:evalName). The following sub-steps omit
      // `route` so the static router does not strip that path back to
      // /evaluate — mirrors the prompt-playground mini-tour pattern.
      "review-evaluator-versions": {
        targetId: TOUR_IDS.evaluatorDetailVersions,
        targetHookId: TASK_TOUR_QUERY_HOOKS.evaluatorDetailVersions,
        actionName: TASK_TOUR_ACTIONS.evaluatorMaximized,
        advance: "manual",
        skipWhenEmptyKey: TASK_TOUR_SKIP_WHEN.noEvaluators,
        popover: { showNext: true, nextLabel: "Next", placement: "right" },
      },
      "review-evaluator-instructions": {
        targetId: TOUR_IDS.evaluatorDetailInstructions,
        targetHookId: TASK_TOUR_QUERY_HOOKS.evaluatorDetailInstructions,
        actionName: TASK_TOUR_ACTIONS.evaluatorMaximized,
        advance: "manual",
        skipWhenEmptyKey: TASK_TOUR_SKIP_WHEN.noEvaluators,
        popover: { showNext: true, nextLabel: "Next", placement: "top" },
      },
      "review-evaluator-model": {
        targetId: TOUR_IDS.evaluatorDetailModel,
        targetHookId: TASK_TOUR_QUERY_HOOKS.evaluatorDetailModel,
        actionName: TASK_TOUR_ACTIONS.evaluatorMaximized,
        advance: "manual",
        skipWhenEmptyKey: TASK_TOUR_SKIP_WHEN.noEvaluators,
        popover: { showNext: true, nextLabel: "Next", placement: "bottom" },
      },
      "open-results-tab": {
        targetId: TOUR_IDS.evaluateResultsTab,
        route: "evaluate",
        actionName: TASK_TOUR_ACTIONS.evaluateResultsOpened,
      },
      "review-result-details": {
        targetId: TOUR_IDS.evaluateResultsFirstRow,
        targetHookId: TASK_TOUR_QUERY_HOOKS.evaluateResultDetails,
        route: "evaluate",
        search: { section: "results" },
        actionName: TASK_TOUR_ACTIONS.evaluateResultDetailsReviewed,
        advance: "action-only",
      },
    },
  },
  traces: {
    steps: {
      "open-observe": {
        targetId: TOUR_IDS.navObserve,
        actionName: TASK_TOUR_ACTIONS.observeOpened,
      },
      "open-trace": {
        targetId: TOUR_IDS.tracesFirstRow,
        targetHookId: TASK_TOUR_QUERY_HOOKS.tracesFirstRow,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.traceOpened,
      },
      "review-spans": {
        targetId: TOUR_IDS.traceDrawerSpans,
        targetHookId: TASK_TOUR_QUERY_HOOKS.traceDrawerSpans,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.spansReviewed,
        advance: "action-only",
        prepareKey: TASK_TOUR_PREPARATIONS.traceOpened,
      },
      "review-annotations": {
        targetId: TOUR_IDS.traceDrawerEvals,
        targetHookId: TASK_TOUR_QUERY_HOOKS.traceDrawerEvals,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.annotationsReviewed,
        advance: "action-only",
        prepareKey: TASK_TOUR_PREPARATIONS.traceOpened,
      },
      "add-feedback": {
        targetId: TOUR_IDS.traceDrawerFeedback,
        targetHookId: TASK_TOUR_QUERY_HOOKS.traceDrawerFeedback,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.feedbackAdded,
        advance: "action-only",
        prepareKey: TASK_TOUR_PREPARATIONS.traceOpened,
      },
    },
  },
  datasets: {
    steps: {
      "open-datasets": {
        targetId: TOUR_IDS.navDatasets,
        actionName: TASK_TOUR_ACTIONS.datasetsOpened,
      },
      "open-preloaded-dataset": {
        targetId: TOUR_IDS.datasetsFirstRow,
        route: "datasets",
        actionName: TASK_TOUR_ACTIONS.datasetOpened,
      },
      // Mini-tour of the dataset detail UI. These are pure orientation beats
      // (manual "Next" popovers, like the prompt-notebook review-* steps), so
      // the spotlight points at a control without the blocking overlay letting
      // a click open it. They omit `route` because `open-preloaded-dataset`
      // already navigated to the dynamic /datasets/:datasetId URL — a static
      // route here would strip it. `actionName` is required but inert under
      // manual advance, so it reuses `datasetOpened`.
      "review-dataset-rows": {
        targetId: TOUR_IDS.datasetTable,
        actionName: TASK_TOUR_ACTIONS.datasetOpened,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "top" },
      },
      "review-dataset-columns": {
        targetId: TOUR_IDS.datasetConfigureColumns,
        actionName: TASK_TOUR_ACTIONS.datasetOpened,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "bottom" },
      },
      "review-dataset-grow": {
        targetId: TOUR_IDS.datasetDataActions,
        actionName: TASK_TOUR_ACTIONS.datasetOpened,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "bottom" },
      },
      "review-dataset-versions": {
        targetId: TOUR_IDS.datasetVersions,
        actionName: TASK_TOUR_ACTIONS.datasetOpened,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "bottom" },
      },
      "review-dataset-experiments": {
        targetId: TOUR_IDS.datasetExperiments,
        actionName: TASK_TOUR_ACTIONS.datasetOpened,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "bottom" },
      },
      "open-traces-for-dataset": {
        targetId: TOUR_IDS.navObserve,
        actionName: TASK_TOUR_ACTIONS.observeOpened,
      },
      "open-trace-for-dataset": {
        targetId: TOUR_IDS.tracesFirstRow,
        targetHookId: TASK_TOUR_QUERY_HOOKS.tracesFirstRow,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.traceOpened,
      },
      "review-trace-actions": {
        targetId: TOUR_IDS.traceActions,
        targetHookId: TASK_TOUR_QUERY_HOOKS.traceActions,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.traceAddedToDataset,
        advance: "manual",
        prepareKey: TASK_TOUR_PREPARATIONS.traceOpened,
        popover: { showNext: true, nextLabel: "Next", placement: "left" },
      },
      "open-add-to-dataset": {
        targetId: TOUR_IDS.traceAddToDatasetAction,
        targetHookId: TASK_TOUR_QUERY_HOOKS.traceAddToDatasetAction,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.traceAddToDatasetOpened,
        prepareKey: TASK_TOUR_PREPARATIONS.traceOpened,
      },
      "save-trace-to-dataset": {
        targetId: TOUR_IDS.traceAddToDatasetDrawer,
        targetHookId: TASK_TOUR_QUERY_HOOKS.traceAddToDatasetDrawer,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.traceAddedToDataset,
        advance: "action-only",
        prepareKey: TASK_TOUR_PREPARATIONS.traceOpened,
      },
      "verify-new-row": {
        targetId: TOUR_IDS.datasetsFirstRow,
        route: "datasets",
        actionName: TASK_TOUR_ACTIONS.datasetRowVerified,
        advance: "action-only",
      },
      "generate-synthetic": {
        targetId: TOUR_IDS.datasetGenerateSynthetic,
        targetHookId: TASK_TOUR_QUERY_HOOKS.datasetGenerateSynthetic,
        actionName: TASK_TOUR_ACTIONS.syntheticDataFinished,
        advance: "action-only",
        formPrefill: {
          targetId: TOUR_IDS.datasetGenerateSyntheticModal,
          values: {
            datasetPurpose: "Data for testing general-purpose wikipedia search agent",
            columnDescriptions: {
              query: "A general-purpose question for the Wikipedia search agent to answer.",
              response: "The expected answer from the Wikipedia search agent.",
            },
            modelName: "gpt-5-nano",
          },
          mode: "empty-only",
        },
      },
    },
  },
  prompts: {
    steps: {
      "open-prompts": {
        targetId: TOUR_IDS.navPrompts,
        actionName: TASK_TOUR_ACTIONS.promptsOpened,
      },
      "open-prompts-tab": {
        targetId: TOUR_IDS.promptsManagementTab,
        route: "prompts",
        actionName: TASK_TOUR_ACTIONS.promptsManagementTabOpened,
      },
      "inspect-prompt": {
        targetId: TOUR_IDS.promptsFirstRow,
        targetHookId: TASK_TOUR_QUERY_HOOKS.demoTaskPromptRow,
        route: "prompts",
        search: { tab: "prompts-management" },
        actionName: TASK_TOUR_ACTIONS.promptInspected,
      },
      "open-in-playground": {
        targetId: TOUR_IDS.promptOpenInPlayground,
        targetHookId: TASK_TOUR_QUERY_HOOKS.promptOpenInPlayground,
        actionName: TASK_TOUR_ACTIONS.promptOpenedInPlayground,
        advance: "action-only",
      },
      // The preceding prompt-detail step navigates to a runtime notebook URL
      // that includes notebookId. Keep this step on the current page so the
      // static router does not strip that dynamic query param.
      "duplicate-prompt-in-playground": {
        targetId: TOUR_IDS.playgroundDuplicatePrompt,
        actionName: TASK_TOUR_ACTIONS.playgroundPromptsCreated,
        popover: { placement: "left" },
      },
      "add-prompt-in-playground": {
        targetId: TOUR_IDS.playgroundAddPrompt,
        actionName: TASK_TOUR_ACTIONS.playgroundPromptsCreated,
        popover: { placement: "left" },
      },
      "review-playground-prompt": {
        targetId: TOUR_IDS.playgroundPromptCard,
        targetHookId: TASK_TOUR_QUERY_HOOKS.playgroundPromptCard,
        actionName: TASK_TOUR_ACTIONS.playgroundPromptsCreated,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "right" },
      },
      "review-playground-controls": {
        targetId: TOUR_IDS.playgroundVariablesButton,
        actionName: TASK_TOUR_ACTIONS.playgroundPromptsCreated,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "bottom" },
      },
      // Nudge the user to persist a prompt as a new version before they leave
      // the notebook. The save control lives on every prompt card, so a query
      // hook scopes the highlight to the newest card. Manual advance (with a
      // Next button) keeps the step unblocked regardless of save state.
      "save-prompt-version": {
        targetId: TOUR_IDS.playgroundSavePrompt,
        targetHookId: TASK_TOUR_QUERY_HOOKS.playgroundSavePrompt,
        actionName: TASK_TOUR_ACTIONS.playgroundPromptsCreated,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "bottom" },
      },
      // Final notebook beat: highlight the whole playground panel and wait for
      // an explicit Next click before `open-create-experiment` navigates the
      // user out to the experiments tab. Without this pause the route change
      // yanks them off the notebook the instant they finish the controls step.
      "review-notebook": {
        targetId: TOUR_IDS.playgroundPanel,
        actionName: TASK_TOUR_ACTIONS.playgroundPromptsCreated,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "left" },
      },
      "open-create-experiment": {
        targetId: TOUR_IDS.promptsExperimentButton,
        targetHookId: TASK_TOUR_QUERY_HOOKS.createExperimentEntry,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentModalOpened,
        advance: "action-only",
      },
      "complete-experiment-info": {
        targetId: TOUR_IDS.createExperimentInfoStep,
        targetHookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfo,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentInfoCompleted,
        advance: "action-only",
        popover: { placement: "left" },
      },
      "complete-prompt-mapping": {
        targetId: TOUR_IDS.createExperimentPromptMappingsStep,
        targetHookId: TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentPromptMappingsCompleted,
        advance: "action-only",
        popover: { placement: "left" },
      },
      "create-experiment": {
        targetId: TOUR_IDS.createExperimentEvalMappingsStep,
        targetHookId: TASK_TOUR_QUERY_HOOKS.createExperimentFinal,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentCreated,
        advance: "action-only",
        popover: { placement: "left" },
      },
    },
  },
  deploy: {
    steps: {
      "open-production-prompt": {
        targetId: TOUR_IDS.promptsFirstRow,
        route: "prompts",
        search: { tab: "prompts-management" },
        actionName: TASK_TOUR_ACTIONS.promptInspected,
      },
      "tag-production": {
        targetId: TOUR_IDS.promptAddTag,
        targetHookId: TASK_TOUR_QUERY_HOOKS.promptTags,
        actionName: TASK_TOUR_ACTIONS.promptPromoted,
        advance: "action-only",
      },
      "reopen-demo-agent": {
        targetId: TOUR_IDS.navDemoAgent,
        actionName: TASK_TOUR_ACTIONS.demoAgentOpened,
        route: "chatbot",
      },
      "send-verification-message": {
        targetId: TOUR_IDS.chatSendPlaceholder,
        actionName: TASK_TOUR_ACTIONS.demoAgentMessageSent,
        route: "chatbot",
        advance: "action-only",
        formPrefill: {
          targetId: TOUR_IDS.chatSendPlaceholder,
          value: "What are AI Agent Evals?",
        },
      },
      "review-verification-message": {
        targetId: TOUR_IDS.chatWindow,
        actionName: TASK_TOUR_ACTIONS.demoAgentMessageSent,
        advance: "manual",
        popover: { showNext: true, nextLabel: "Next", placement: "top" },
      },
      "verify-eval-passes": {
        targetId: TOUR_IDS.navObserve,
        actionName: TASK_TOUR_ACTIONS.deployVerified,
      },
      // Closing beat: drop the user on the freshest trace and advance when they
      // open it. Reuses the traces-first-row query hook (the latest trace sorts
      // to the top of the table) and the `traceOpened` action emitted when the
      // drawer opens — same pattern as the `open-trace` step.
      "review-latest-trace": {
        targetId: TOUR_IDS.tracesFirstRow,
        targetHookId: TASK_TOUR_QUERY_HOOKS.tracesFirstRow,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.traceOpened,
      },
    },
  },
};
