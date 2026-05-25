import { TOUR_IDS, type TourId } from "./selectors";

/**
 * Real-app sub-route under `/tasks/:taskId/`. Mirrors the keys in
 * `App.tsx` so we never have to invent route strings ad-hoc.
 */
export type TaskSubRoute = "overview" | "traces" | "test" | "evaluate" | "datasets" | "prompts";

export interface TaskTourSearchParams {
  /** Optional query params appended to the route (`?section=evaluators` etc.). */
  search?: Record<string, string>;
}

export interface TaskTourItem {
  id: string;
  title: string;
  instructions: string;
  targetId: TourId;
  /**
   * Optional route the engine should be on before resolving the target. Omit
   * when the target lives in the persistent task shell (e.g. sidebar nav
   * items), so the engine doesn't force-navigate the user away from whichever
   * page they happen to be on.
   */
  route?: TaskSubRoute;
  /** Optional search params for the route. */
  search?: Record<string, string>;
  /**
   * Name of the custom event the engine listens for to advance. The panel's
   * "Mark step complete" button dispatches this; natural clicks on the
   * spotlighted target also advance the engine via the built-in click
   * trigger. Keep these globally unique to avoid cross-step bleed.
   */
  eventName: string;
  /**
   * Advance strategy. `"click+event"` (default) attaches both triggers so
   * natural interaction OR the "Mark step complete" button advances. Use
   * `"event-only"` for placeholder targets where clicking the spotlight host
   * shouldn't auto-advance (e.g. when the target is a coarse page-level
   * element rather than a true call-to-action).
   */
  advance?: "click+event" | "event-only";
}

export interface TaskTourSection {
  id: string;
  title: string;
  kicker: string;
  intro: {
    heading: string;
    body: string;
    /** If true, the section intro renders the ADLC flywheel hero. */
    showFlywheel?: boolean;
    scenario?: { label: string; text: string };
    cta: string;
  };
  items: TaskTourItem[];
  /** Stub sections collapse to a single auto-advancing placeholder step. */
  stub?: boolean;
}

export const TASK_TOUR_TITLE = "Evals 101: Build a Production-Grade Agent";
export const TASK_TOUR_SHORT_NAME = "Evals 101";
export const TASK_TOUR_SUBTITLE = "A guided tour of the Arthur Development Lifecycle (ADLC)";

/**
 * Author-friendly representation of the tour. Each item maps 1:1 to an engine
 * `StepConfig`; sections with `items.length === 0` collapse to a stub step.
 */
export const TASK_TOUR_SECTIONS: TaskTourSection[] = [
  {
    id: "intro",
    title: "Welcome to the ADLC",
    kicker: "Section 1 of 7",
    intro: {
      heading: "Welcome to the ADLC",
      body: "The Arthur Development Lifecycle is how teams ship agents they can trust. You'll iterate through five stages: build, evaluate, trace, refine, and deploy.",
      showFlywheel: true,
      scenario: {
        label: "Your scenario",
        text: "You've just opened a task in Arthur. We'll walk through the lifecycle here — interact, evaluate, trace, then iterate — using the surfaces this task already exposes.",
      },
      cta: "Start tour",
    },
    items: [],
    stub: true,
  },
  {
    id: "agent",
    title: "Interact with the agent",
    kicker: "Section 2 of 7",
    intro: {
      heading: "Meet your agent",
      body: "Before you can fix an agent, you have to use it. Arthur's Test surface lets you run notebooks and experiments against the agent so every interaction lands as a trace.",
      scenario: {
        label: "What you'll do",
        text: "Open the Test view from the sidebar, then start a notebook. Each notebook run produces a trace we'll dig into later.",
      },
      cta: "Open Test",
    },
    items: [
      {
        id: "open-test",
        title: "Open the Test view",
        instructions: "Click Test in the left sidebar to open the agent testing surface.",
        targetId: TOUR_IDS.navTest,
        eventName: "task-tour:test-opened",
      },
      {
        id: "start-notebook",
        title: "Start a notebook",
        instructions: "Click + Notebook to create a new agent notebook, or open an existing one from the list.",
        targetId: TOUR_IDS.testNotebookCreate,
        route: "test",
        search: { section: "agentic-notebooks" },
        eventName: "task-tour:notebook-started",
      },
      {
        id: "send-message",
        title: "Send a message to the agent",
        instructions:
          "Inside the notebook, send any general-knowledge question. Arthur will record the run as a trace we can inspect from Observe. (Mark complete when you've sent one.)",
        targetId: TOUR_IDS.chatSendPlaceholder,
        route: "test",
        search: { section: "agentic-notebooks" },
        eventName: "task-tour:message-sent",
        advance: "event-only",
      },
    ],
  },
  {
    id: "evals",
    title: "Look at evals",
    kicker: "Section 3 of 7",
    intro: {
      heading: "Measure before you change",
      body: "Evals are the contract you set with your agent. Before tuning prompts or swapping models, you need to know how the agent is being measured — and against what bar.",
      scenario: {
        label: "What you'll do",
        text: "Open the Evaluate view and look at the first evaluator. The threshold and run cadence are what determine whether traces pass.",
      },
      cta: "Open Evaluate",
    },
    items: [
      {
        id: "open-evaluate",
        title: "Open Evaluate",
        instructions: "Click Evaluate in the sidebar to see the evaluators currently running on this task.",
        targetId: TOUR_IDS.navEvaluate,
        eventName: "task-tour:evaluate-opened",
      },
      {
        id: "review-evaluator",
        title: "Review an evaluator",
        instructions: "Open the first evaluator card. The threshold, model, and run cadence tell you when a trace will pass or fail.",
        targetId: TOUR_IDS.evaluatorsFirstCard,
        route: "evaluate",
        eventName: "task-tour:evaluator-reviewed",
      },
    ],
  },
  {
    id: "traces",
    title: "Look at traces",
    kicker: "Section 4 of 7",
    intro: {
      heading: "Follow the request, span by span",
      body: "A trace is the timeline of everything the agent did to produce one answer — retrieval calls, model invocations, post-processing, evals. Continuous Evals run on every trace automatically.",
      scenario: {
        label: "What you'll do",
        text: "Open Observe, drill into your latest trace, read the spans + eval annotations, and leave manual feedback so the agent can be improved.",
      },
      cta: "Open Observe",
    },
    items: [
      {
        id: "open-observe",
        title: "Open Observe",
        instructions: "Click Observe in the sidebar to see the trail of requests this agent has generated.",
        targetId: TOUR_IDS.navObserve,
        eventName: "task-tour:observe-opened",
      },
      {
        id: "open-trace",
        title: "Open the latest trace",
        instructions: "Click the top row to open the trace drawer for the most recent run.",
        targetId: TOUR_IDS.tracesFirstRow,
        route: "traces",
        eventName: "task-tour:trace-opened",
      },
      {
        id: "review-spans",
        title: "Review the trace and spans",
        instructions: "Each span shows a step the agent took. Look at latency, cost, tokens — and how time is distributed across spans.",
        targetId: TOUR_IDS.traceDrawerSpans,
        route: "traces",
        eventName: "task-tour:spans-reviewed",
        advance: "event-only",
      },
      {
        id: "review-annotations",
        title: "Review the eval annotations",
        instructions: "Continuous Evals run automatically on every trace. The annotations on this trace are the signals we'd chase to improve it.",
        targetId: TOUR_IDS.traceDrawerEvals,
        route: "traces",
        eventName: "task-tour:annotations-reviewed",
        advance: "event-only",
      },
      {
        id: "add-feedback",
        title: "Add manual feedback",
        instructions:
          "Manual feedback is how humans (or your own app) tell Arthur something an eval can't. Leave a quick note about this answer. (Mark complete when you've added one.)",
        targetId: TOUR_IDS.traceDrawerFeedback,
        route: "traces",
        eventName: "task-tour:feedback-added",
        advance: "event-only",
      },
    ],
  },
  {
    id: "datasets",
    title: "Work with datasets",
    kicker: "Section 5 of 7",
    stub: true,
    intro: {
      heading: "Build a test suite",
      body: "Datasets are the test cases your agent has to pass before every release. Promote real traces (including the ones you just annotated) into a dataset, then enrich it with synthetic examples.",
      scenario: {
        label: "Coming up",
        text: "Datasets-driven evaluation isn't fully wired into the tour yet — for now this is a placeholder section so you can see the full ADLC flow.",
      },
      cta: "Continue",
    },
    items: [],
  },
  {
    id: "prompts",
    title: "Experiment with prompts",
    kicker: "Section 6 of 7",
    stub: true,
    intro: {
      heading: "Tune, then prove it",
      body: "The Prompt surface lets you try variations side by side. Experiments run those prompts against your dataset and evals so you can ship with confidence.",
      scenario: { label: "Coming up", text: "Placeholder for now — this will become a guided prompt-tuning flow." },
      cta: "Continue",
    },
    items: [],
  },
  {
    id: "deploy",
    title: "Deploy and verify",
    kicker: "Section 7 of 7",
    stub: true,
    intro: {
      heading: "Ship and watch",
      body: "Tag the winning prompt as production, then re-run the agent and confirm your evals are passing on fresh traces.",
      scenario: { label: "Coming up", text: "Placeholder for now — deployment tooling is the next iteration." },
      cta: "Finish the tour",
    },
    items: [],
  },
];

export function findSection(sectionId: string): TaskTourSection | undefined {
  return TASK_TOUR_SECTIONS.find((s) => s.id === sectionId);
}

export function findItem(sectionId: string, itemId: string): TaskTourItem | undefined {
  return findSection(sectionId)?.items.find((i) => i.id === itemId);
}
