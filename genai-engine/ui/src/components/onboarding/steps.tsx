import type { Placement } from "react-joyride";

import { type DataTourKey, tourSelector } from "./data-tour";
import { tourRoutes } from "./routes";

type StepPlacement = Placement | "auto" | "center";

export const STEP_IDS = {
  OPEN_CHAT: "open-chat",
  SEND_MESSAGE: "send-message",
  VIEW_TRACES: "view-traces",
  INSPECT_TRACE: "inspect-trace",
  REVIEW_TRACE: "review-trace",
  VIEW_DATASETS: "view-datasets",
  BROWSE_DATASETS: "browse-datasets",
  VIEW_PROMPTS: "view-prompts",
  EDIT_PROMPT: "edit-prompt",
  RUN_EXPERIMENT: "run-experiment",
  CHOOSE_EXPERIMENT_TYPE: "choose-experiment-type",
} as const;
export type StepId = (typeof STEP_IDS)[keyof typeof STEP_IDS];

export const SKIP_TO_END = "end" as const;
export type SkipTarget = StepId | typeof SKIP_TO_END;

// DATA_TOUR key, or raw selector for third-party DOM we don't own.
export type StepTarget = DataTourKey | { raw: string };

export const resolveStepTarget = (target: StepTarget): string => (typeof target === "string" ? tourSelector(target) : target.raw);

export interface StepRoute {
  href: (taskId: string) => string;
  // Destination: wait for the user to arrive, then advance. Default is precondition (navigate on enter).
  advanceOnArrival?: boolean;
}

export interface StepDemo {
  message?: string;
}

export interface TourStep {
  id: StepId;
  label: string;
  title: string;
  body: string;
  target: StepTarget;
  placement: StepPlacement;
  route?: StepRoute;
  spotlightClicks: boolean;
  // Disables joyride's overlay click-shield
  overlayClickThrough?: boolean;
  // Steps sharing a skipTo form an implicit group; Skip jumps past the rest of the group.
  skipTo?: SkipTarget;
  // Run the registered Next-action on skip too
  runActionOnSkip?: boolean;
  // Replayed by the progress widget when the user opens this step out of order.
  prerequisites?: StepId[];
  demo?: StepDemo;
}

export const STEPS: TourStep[] = [
  {
    id: STEP_IDS.OPEN_CHAT,
    label: "Open the demo agent",
    title: "Open the AI assistant",
    body: "Click the chat icon in the bottom-right corner to open the demo agent.",
    target: "CHATBOT_FAB",
    placement: "left-end",
    spotlightClicks: true,
    skipTo: STEP_IDS.VIEW_TRACES,
  },
  {
    id: STEP_IDS.SEND_MESSAGE,
    label: "Send a message to the demo agent",
    title: "Send a message",
    body: "Type a question and hit send. The demo agent will respond and generate a trace you can inspect.",
    target: "CHATBOT_PANEL",
    placement: "left",
    spotlightClicks: true,
    skipTo: STEP_IDS.VIEW_TRACES,
    prerequisites: [STEP_IDS.OPEN_CHAT],
    demo: { message: "Hi! I'm trying out Arthur Engine!" },
  },
  {
    id: STEP_IDS.VIEW_TRACES,
    label: "View your traces",
    title: "Open the Observe view",
    body: "Every request to the agent is captured as a trace. Click 'Observe' in the sidebar to see them.",
    target: "NAV_TRACES",
    placement: "right",
    route: { href: tourRoutes.traces, advanceOnArrival: true },
    spotlightClicks: true,
    skipTo: STEP_IDS.VIEW_DATASETS,
  },
  {
    id: STEP_IDS.INSPECT_TRACE,
    label: "Open a trace",
    title: "Open a trace",
    body: "Click any trace row to open its details.",
    target: "TRACES_TABLE",
    placement: "top",
    route: { href: tourRoutes.traces },
    spotlightClicks: true,
    skipTo: STEP_IDS.VIEW_DATASETS,
  },
  {
    id: STEP_IDS.REVIEW_TRACE,
    label: "Review the trace and eval scores",
    title: "Review the details",
    body: "Look through the prompt, response, and eval scores in the side panel, then close it when you're ready.",
    target: "TRACE_DRAWER",
    placement: "left",
    spotlightClicks: true,
    overlayClickThrough: true,
    skipTo: STEP_IDS.VIEW_DATASETS,
    runActionOnSkip: true,
    prerequisites: [STEP_IDS.INSPECT_TRACE],
  },
  {
    id: STEP_IDS.VIEW_DATASETS,
    label: "Navigate to Datasets",
    title: "Browse your datasets",
    body: "Datasets are the test sets used to evaluate prompts. Click 'Dataset' in the sidebar to see what's available.",
    target: "NAV_DATASETS",
    placement: "right",
    route: { href: tourRoutes.datasets, advanceOnArrival: true },
    spotlightClicks: true,
    skipTo: STEP_IDS.VIEW_PROMPTS,
  },
  {
    id: STEP_IDS.BROWSE_DATASETS,
    label: "Look around your datasets",
    title: "Look around",
    body: "These are the test sets used to evaluate prompts. Take a look around when you're ready, then click Next.",
    target: "DATASETS_TABLE",
    placement: "top",
    route: { href: tourRoutes.datasets },
    spotlightClicks: true,
    skipTo: STEP_IDS.VIEW_PROMPTS,
  },
  {
    id: STEP_IDS.VIEW_PROMPTS,
    label: "Navigate to Prompts",
    title: "Open the Prompts view",
    body: "Prompts are the templates that drive your task. Click 'Prompts' in the sidebar to see what's available.",
    target: "NAV_PROMPTS",
    placement: "right",
    route: { href: tourRoutes.promptsManagement, advanceOnArrival: true },
    spotlightClicks: true,
    skipTo: STEP_IDS.RUN_EXPERIMENT,
  },
  {
    id: STEP_IDS.EDIT_PROMPT,
    label: "Open a prompt to inspect it",
    title: "Inspect a prompt",
    body: "Click any prompt row to open its detail view, where you can see versions, tags, and make edits.",
    target: "PROMPTS_TABLE",
    placement: "top",
    route: { href: tourRoutes.promptsManagement },
    spotlightClicks: true,
    skipTo: STEP_IDS.RUN_EXPERIMENT,
  },
  {
    id: STEP_IDS.RUN_EXPERIMENT,
    label: "Open the experiment menu",
    title: "Launch an experiment",
    body: "Experiments let you test prompt variations side-by-side against a dataset. Click 'Experiment' to get started.",
    target: "CREATE_EXPERIMENT_BUTTON",
    placement: "left-start",
    route: { href: tourRoutes.promptsExperiments },
    spotlightClicks: true,
    skipTo: SKIP_TO_END,
  },
  {
    id: STEP_IDS.CHOOSE_EXPERIMENT_TYPE,
    label: "Pick a starting point",
    title: "Pick a starting point",
    body: "Choose 'Create New' to start fresh, or 'Create from Existing' to clone an existing experiment.",
    target: { raw: ".MuiMenu-paper" },
    placement: "left",
    spotlightClicks: true,
    skipTo: SKIP_TO_END,
    prerequisites: [STEP_IDS.RUN_EXPERIMENT],
  },
];

export const findStep = (id: StepId): TourStep | undefined => STEPS.find((s) => s.id === id);

export const getStepDemo = (id: StepId): StepDemo | undefined => findStep(id)?.demo;
