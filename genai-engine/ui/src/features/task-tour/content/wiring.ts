import { TOUR_IDS, type TourId } from "../selectors";
import { TASK_TOUR_ACTIONS } from "../tourActions";

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
export type TaskSubRoute = "overview" | "traces" | "test" | "evaluate" | "datasets" | "prompts" | "prompts-management" | "playgrounds/prompts";

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
  advance?: "click+action" | "action-only";
  prepareKey?: string;
  skipWhenEmptyKey?: string;
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
  tracesFirstRow: "task-tour.tracesFirstRow",
  traceDrawerSpans: "task-tour.traceDrawerSpans",
  traceDrawerEvals: "task-tour.traceDrawerEvals",
  traceDrawerFeedback: "task-tour.traceDrawerFeedback",
  traceDrawerAddToDataset: "task-tour.traceDrawerAddToDataset",
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
  agent: { steps: {} },
  evals: {
    steps: {
      "open-evaluate": {
        targetId: TOUR_IDS.navEvaluate,
        actionName: TASK_TOUR_ACTIONS.evaluateOpened,
      },
      "review-evaluator": {
        targetId: TOUR_IDS.evaluatorsFirstCard,
        route: "evaluate",
        actionName: TASK_TOUR_ACTIONS.evaluatorReviewed,
        skipWhenEmptyKey: TASK_TOUR_SKIP_WHEN.noEvaluators,
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
      "add-trace-to-dataset": {
        targetId: TOUR_IDS.traceDrawerAddToDataset,
        targetHookId: TASK_TOUR_QUERY_HOOKS.traceDrawerAddToDataset,
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
        actionName: TASK_TOUR_ACTIONS.syntheticDataGenerated,
        advance: "action-only",
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
        route: "prompts",
        actionName: TASK_TOUR_ACTIONS.promptInspected,
      },
      // Routes to the Notebooks tab — the entry point for the playground
      // workflow described in the markdown copy. The actual target
      // (`playgroundAddPrompt`) lives inside the playground, reached by
      // opening a notebook from the listing; the step stays `action-only`
      // because we can't statically deep-link to a notebook's playground
      // URL (it requires a `notebookId` we don't know at config time).
      "create-prompts-in-playground": {
        targetId: TOUR_IDS.playgroundAddPrompt,
        route: "prompts",
        search: { tab: "notebooks" },
        actionName: TASK_TOUR_ACTIONS.playgroundPromptsCreated,
        advance: "action-only",
      },
      "run-experiment": {
        targetId: TOUR_IDS.promptsExperimentButton,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.experimentRun,
      },
    },
  },
  deploy: {
    steps: {
      "tag-production": {
        targetId: TOUR_IDS.promptAddTag,
        actionName: TASK_TOUR_ACTIONS.promptPromoted,
        advance: "action-only",
      },
      "verify-eval-passes": {
        targetId: TOUR_IDS.navObserve,
        route: "traces",
        actionName: TASK_TOUR_ACTIONS.deployVerified,
        advance: "action-only",
      },
    },
  },
};
