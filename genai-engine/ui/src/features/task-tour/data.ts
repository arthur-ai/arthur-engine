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
 *
 * The tour is anchored on a single worked example: an agent that is
 * consistently producing answers outside the readability bar this team set.
 * Every section's copy, scenario, and step instructions reinforce that
 * scenario — the user diagnoses the readability failures with traces +
 * continuous evals, captures them in a dataset, fixes them in the prompt
 * playground, and ships the winning version.
 */
export const TASK_TOUR_SECTIONS: TaskTourSection[] = [
  {
    id: "intro",
    title: "Welcome to the ADLC",
    kicker: "Section 1 of 7",
    intro: {
      heading: "Welcome to the ADLC",
      body: "The Arthur Development Lifecycle is how teams ship agents they can trust. Over the next few minutes you'll iterate through every stage — interact, measure, observe, refine, and deploy — using one real failure mode as your worked example.",
      showFlywheel: true,
      scenario: {
        label: "Your scenario",
        text: "The agent on this task is consistently responding outside its readability parameters — answers that should be plain-language are coming back too dense for the audience. We'll use the ADLC to find the failure, fix the prompt, and prove the fix held.",
      },
      cta: "Start tour",
    },
    items: [],
    stub: true,
  },
  {
    id: "agent",
    title: "Interact with the Demo Agent",
    kicker: "Section 2 of 7",
    // Disabled / stubbed until the bundled Demo Agent ships. The current
    // Test → Notebook flow is a placeholder, not a real agent we can wire
    // tour spotlights against, so this section renders as an intro-only
    // primer that previews the interaction.
    stub: true,
    intro: {
      heading: "Meet your Demo Agent",
      body: "Once the bundled Demo Agent ships, you'll open it from the task sidebar, send it a question, and Arthur will record the run as a trace we'll inspect together. For now this section is a preview — keep going to see how Arthur handles the readability failures the agent has already produced.",
      scenario: {
        label: "Coming up",
        text: "Two-step flow when the Demo Agent lands: (1) Open the Demo Agent from the sidebar — we'll describe what it does. (2) Send it any general-knowledge question and watch the trace land in Observe.",
      },
      cta: "Continue",
    },
    items: [],
  },
  {
    id: "evals",
    title: "Look at evals",
    kicker: "Section 3 of 7",
    intro: {
      heading: "Measure before you change",
      body: "Evals are the contract you set with your agent. Before tuning prompts or swapping models you need to know how the agent is being measured — and against what bar — so any change can be judged objectively.",
      scenario: {
        label: "What you'll do",
        text: "Open Evaluate and inspect the first evaluator. Pay attention to the model that judges each trace and the variables that get fed into the eval — together with the threshold, they decide whether a trace passes or fails.",
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
        instructions:
          "Open the first evaluator card. Each evaluator runs a model against a set of variables pulled from every trace, then scores the result against a threshold — that's how Arthur decides whether the agent is meeting the bar.",
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
      body: "A trace is the timeline of everything the agent did to produce one answer — retrieval calls, model invocations, post-processing, evals. Continuous Evals run on every trace automatically, so you can spot failure patterns the moment they happen.",
      scenario: {
        label: "What you'll do",
        text: "Open Observe, drill into a trace, walk through the spans, read the eval annotations, and leave manual feedback. We'll specifically call out where the readability eval is failing — that's the signal you'll fix later in this tour.",
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
        title: "Open a trace",
        instructions:
          "Click the top row to open the most recent trace. Any trace works for this exercise — we'll use whichever you pick to walk through what's inside.",
        targetId: TOUR_IDS.tracesFirstRow,
        route: "traces",
        eventName: "task-tour:trace-opened",
      },
      {
        id: "review-spans",
        title: "Review the trace and spans",
        instructions:
          "A trace is the full request; each span is one step the agent took (retrieval, model call, post-processing). Look at latency, cost, and tokens to see where time and money are going.",
        targetId: TOUR_IDS.traceDrawerSpans,
        route: "traces",
        eventName: "task-tour:spans-reviewed",
        advance: "event-only",
      },
      {
        id: "review-annotations",
        title: "Review the eval annotations",
        instructions:
          "Continuous Evals attach automatically to every trace. Notice the Readability Eval is failing here — that's the live signal pointing at the failure mode we're going to fix in the prompt playground.",
        targetId: TOUR_IDS.traceDrawerEvals,
        route: "traces",
        eventName: "task-tour:annotations-reviewed",
        advance: "event-only",
      },
      {
        id: "add-feedback",
        title: "Add manual feedback",
        instructions:
          "Manual feedback is how humans (or your own app, via the API) tell Arthur something an eval can't. Leave a quick note about this answer — devs use it to triage and apps can post it programmatically. (Mark complete when you've added one.)",
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
    intro: {
      heading: "Build a test suite",
      body: "Datasets are the test cases your agent has to pass before every release. Promote real traces — including the readability failure you just annotated — into a dataset, then enrich it with synthetic examples so future regressions get caught automatically.",
      scenario: {
        label: "What you'll do",
        text: "Open the pre-loaded dataset, then add the failing trace from Observe into it, return to the dataset to see the new row land, and (optional) generate a few synthetic rows to broaden coverage.",
      },
      cta: "Open Datasets",
    },
    items: [
      {
        id: "open-datasets",
        title: "Open Datasets",
        instructions: "Click Dataset in the sidebar to see the test sets available on this task.",
        targetId: TOUR_IDS.navDatasets,
        eventName: "task-tour:datasets-opened",
      },
      {
        id: "open-preloaded-dataset",
        title: "Open the pre-loaded dataset",
        instructions:
          "Click the top dataset row. This is the test suite developers use to make sure the agent doesn't regress on cases we already know matter.",
        targetId: TOUR_IDS.datasetsFirstRow,
        route: "datasets",
        eventName: "task-tour:dataset-opened",
      },
      {
        id: "add-trace-to-dataset",
        title: "Add a trace to the dataset",
        instructions:
          "Head back to Observe, open the trace with the failing readability eval, and use 'Add to Dataset' to capture it as a test case. This is how you turn a real-world failure into a permanent regression check. (Mark complete when you've added one.)",
        targetId: TOUR_IDS.traceDrawerAddToDataset,
        route: "traces",
        eventName: "task-tour:trace-added-to-dataset",
        advance: "event-only",
      },
      {
        id: "verify-new-row",
        title: "Confirm the new row landed",
        instructions:
          "Reopen Datasets and click the same dataset — the trace you just added should be a new row, ready to be replayed against future prompt versions.",
        targetId: TOUR_IDS.datasetsFirstRow,
        route: "datasets",
        eventName: "task-tour:dataset-row-verified",
        advance: "event-only",
      },
      {
        id: "generate-synthetic",
        title: "Generate synthetic data (optional)",
        instructions:
          "Click Generate to enrich the dataset with 5–10 synthetic rows based on the examples already captured. Synthetic data broadens test coverage without waiting for real users to hit edge cases. (Mark complete when you've generated some — or skip if you'd rather move on.)",
        targetId: TOUR_IDS.datasetGenerateSynthetic,
        eventName: "task-tour:synthetic-data-generated",
        advance: "event-only",
      },
    ],
  },
  {
    id: "prompts",
    title: "Experiment with prompts",
    kicker: "Section 6 of 7",
    intro: {
      heading: "Tune, then prove it",
      body: "A prompt is a collection of messages, variables, and a model — change any of them and you've got a candidate fix. The playground lets you try variations side-by-side, and Experiments run those candidates against your dataset and evals so you can ship with confidence.",
      scenario: {
        label: "What you'll do",
        text: "Inspect the existing prompt, open the playground and draft 2–3 variants that fix the readability failure, then run an experiment against the dataset and evals to see which variant wins.",
      },
      cta: "Open Prompts",
    },
    items: [
      {
        id: "open-prompts",
        title: "Open Prompts",
        instructions: "Click Prompt in the sidebar to see the prompts powering this agent.",
        targetId: TOUR_IDS.navPrompts,
        eventName: "task-tour:prompts-opened",
      },
      {
        id: "inspect-prompt",
        title: "Inspect a prompt",
        instructions:
          "Open the Prompts tab and click the top prompt. Each prompt is a bundle of messages, variables, and a model — change any of those and you've got a new version worth comparing.",
        targetId: TOUR_IDS.promptsFirstRow,
        route: "prompts",
        search: { tab: "prompts-management" },
        eventName: "task-tour:prompt-inspected",
      },
      {
        id: "create-prompts-in-playground",
        title: "Draft variants in the playground",
        instructions:
          "Switch to the Notebooks tab, open a notebook, and use Add Prompt to draft 2–3 variants that tighten the system prompt for readability. You can also try a different model or tweak variables — anything that might fix the failure. (Mark complete when you've drafted some.)",
        targetId: TOUR_IDS.playgroundAddPrompt,
        eventName: "task-tour:playground-prompts-created",
        advance: "event-only",
      },
      {
        id: "run-experiment",
        title: "Run an experiment",
        instructions:
          "Switch to the Runs tab and click Experiment. Configure it with your dataset (the one with the captured failure), your candidate prompts, and the evals — then run it. This is the final ADLC checkpoint before you ship.",
        targetId: TOUR_IDS.promptsExperimentButton,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        eventName: "task-tour:experiment-run",
        advance: "event-only",
      },
    ],
  },
  {
    id: "deploy",
    title: "Deploy and verify",
    kicker: "Section 7 of 7",
    intro: {
      heading: "Ship and watch",
      body: "Tag the winning prompt as production, then re-run the agent and confirm the readability eval is green on fresh traces. That's the loop closing — the failure you found in Observe is the failure you just shipped a fix for.",
      scenario: {
        label: "What you'll do",
        text: "On the prompt detail view, promote the best experiment candidate to production. Then return to Observe and verify a new trace clears the readability eval.",
      },
      cta: "Open Prompts",
    },
    items: [
      {
        id: "tag-production",
        title: "Tag the winning prompt as production",
        instructions:
          "Open the prompt detail view, click the tag icon next to the version chips, and check 'Promote to Production'. Whichever version you tag becomes the one production traffic uses. (Mark complete when you've tagged it.)",
        targetId: TOUR_IDS.promptAddTag,
        eventName: "task-tour:prompt-promoted",
        advance: "event-only",
      },
      {
        id: "verify-eval-passes",
        title: "Verify the eval passes",
        instructions:
          "Head to Observe and look at the most recent trace produced by the agent. With the new production prompt in place, the Readability Eval should now be passing — that's your proof the fix held. (Mark complete when you've checked.)",
        targetId: TOUR_IDS.navObserve,
        eventName: "task-tour:deploy-verified",
        advance: "event-only",
      },
    ],
  },
];

export function findSection(sectionId: string): TaskTourSection | undefined {
  return TASK_TOUR_SECTIONS.find((s) => s.id === sectionId);
}

export function findItem(sectionId: string, itemId: string): TaskTourItem | undefined {
  return findSection(sectionId)?.items.find((i) => i.id === itemId);
}
