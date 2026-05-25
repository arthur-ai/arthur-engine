import { TOUR_IDS, type TourId } from "../selectors";
import { TASK_TOUR_EVENTS } from "../tourEventNames";

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
 *   [selectors.ts](../selectors.ts).
 * - `eventName` — globally-unique custom-event name the panel dispatches and
 *   the engine listens for to advance.
 * - `route` — optional route the engine navigates to before resolving the
 *   target. Omit when the target lives in the persistent task shell.
 * - `search` — optional search params appended to the route.
 * - `advance` — `"click+event"` (default) attaches both triggers; use
 *   `"event-only"` for coarse / page-level placeholder targets where a click
 *   shouldn't auto-advance.
 */
export interface StepWiring {
  targetId: TourId;
  eventName: string;
  route?: TaskSubRoute;
  search?: Record<string, string>;
  advance?: "click+event" | "event-only";
}

/**
 * Per-section wiring. `stub: true` collapses the section to a single
 * auto-advancing placeholder step driven by the section intro modal.
 */
export interface SectionWiring {
  stub?: boolean;
  steps: Record<string, StepWiring>;
}

/**
 * The complete engineering wiring for the tour. Keys are section IDs that
 * must match the `id` field in the corresponding markdown frontmatter; inner
 * step keys must match the `## step: <id>` headings in the body. The loader
 * enforces both invariants at module load.
 */
export const TASK_TOUR_WIRING: Record<string, SectionWiring> = {
  intro: {
    stub: true,
    steps: {},
  },
  agent: {
    stub: true,
    steps: {},
  },
  evals: {
    steps: {
      "open-evaluate": {
        targetId: TOUR_IDS.navEvaluate,
        eventName: TASK_TOUR_EVENTS.evaluateOpened,
      },
      "review-evaluator": {
        targetId: TOUR_IDS.evaluatorsFirstCard,
        route: "evaluate",
        eventName: TASK_TOUR_EVENTS.evaluatorReviewed,
      },
    },
  },
  traces: {
    steps: {
      "open-observe": {
        targetId: TOUR_IDS.navObserve,
        eventName: TASK_TOUR_EVENTS.observeOpened,
      },
      "open-trace": {
        targetId: TOUR_IDS.tracesFirstRow,
        route: "traces",
        eventName: TASK_TOUR_EVENTS.traceOpened,
      },
      "review-spans": {
        targetId: TOUR_IDS.traceDrawerSpans,
        route: "traces",
        eventName: TASK_TOUR_EVENTS.spansReviewed,
        advance: "event-only",
      },
      "review-annotations": {
        targetId: TOUR_IDS.traceDrawerEvals,
        route: "traces",
        eventName: TASK_TOUR_EVENTS.annotationsReviewed,
        advance: "event-only",
      },
      "add-feedback": {
        targetId: TOUR_IDS.traceDrawerFeedback,
        route: "traces",
        eventName: TASK_TOUR_EVENTS.feedbackAdded,
        advance: "event-only",
      },
    },
  },
  datasets: {
    steps: {
      "open-datasets": {
        targetId: TOUR_IDS.navDatasets,
        eventName: TASK_TOUR_EVENTS.datasetsOpened,
      },
      "open-preloaded-dataset": {
        targetId: TOUR_IDS.datasetsFirstRow,
        route: "datasets",
        eventName: TASK_TOUR_EVENTS.datasetOpened,
      },
      "add-trace-to-dataset": {
        targetId: TOUR_IDS.traceDrawerAddToDataset,
        route: "traces",
        eventName: TASK_TOUR_EVENTS.traceAddedToDataset,
        advance: "event-only",
      },
      "verify-new-row": {
        targetId: TOUR_IDS.datasetsFirstRow,
        route: "datasets",
        eventName: TASK_TOUR_EVENTS.datasetRowVerified,
        advance: "event-only",
      },
      "generate-synthetic": {
        targetId: TOUR_IDS.datasetGenerateSynthetic,
        eventName: TASK_TOUR_EVENTS.syntheticDataGenerated,
        advance: "event-only",
      },
    },
  },
  prompts: {
    steps: {
      "open-prompts": {
        targetId: TOUR_IDS.navPrompts,
        eventName: TASK_TOUR_EVENTS.promptsOpened,
      },
      "inspect-prompt": {
        targetId: TOUR_IDS.promptsFirstRow,
        route: "prompts",
        search: { tab: "prompts-management" },
        eventName: TASK_TOUR_EVENTS.promptInspected,
      },
      // Routes to the Notebooks tab — the entry point for the playground
      // workflow described in the markdown copy. The actual target
      // (`playgroundAddPrompt`) lives inside the playground, reached by
      // opening a notebook from the listing; the step stays `event-only`
      // because we can't statically deep-link to a notebook's playground
      // URL (it requires a `notebookId` we don't know at config time).
      "create-prompts-in-playground": {
        targetId: TOUR_IDS.playgroundAddPrompt,
        route: "prompts",
        search: { tab: "notebooks" },
        eventName: TASK_TOUR_EVENTS.playgroundPromptsCreated,
        advance: "event-only",
      },
      // Target IS clickable (the Experiment button) and the route lands us
      // directly on the page that owns it — converting to default
      // `click+event` so the user can advance by clicking the button OR
      // ticking the panel checkbox.
      "run-experiment": {
        targetId: TOUR_IDS.promptsExperimentButton,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        eventName: TASK_TOUR_EVENTS.experimentRun,
      },
    },
  },
  deploy: {
    steps: {
      // `tag-production` and `verify-eval-passes` stay `event-only`: the
      // first needs a `prompts/:promptName` deep-link we can't resolve
      // statically (depends on which prompt the user picked earlier);
      // the second is a verification step the user performs by reading
      // a fresh trace, not by clicking the highlighted nav.
      "tag-production": {
        targetId: TOUR_IDS.promptAddTag,
        eventName: TASK_TOUR_EVENTS.promptPromoted,
        advance: "event-only",
      },
      "verify-eval-passes": {
        targetId: TOUR_IDS.navObserve,
        route: "traces",
        eventName: TASK_TOUR_EVENTS.deployVerified,
        advance: "event-only",
      },
    },
  },
};
