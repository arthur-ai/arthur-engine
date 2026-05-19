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

export const MAJOR_TASK_IDS = {
  CHAT: "chat",
  OBSERVE: "observe",
  DATASETS: "datasets",
  PROMPTS: "prompts",
  EXPERIMENTS: "experiments",
} as const;
export type MajorTaskId = (typeof MAJOR_TASK_IDS)[keyof typeof MAJOR_TASK_IDS];

// DATA_TOUR key, or raw selector for third-party DOM we don't own.
export type StepTarget = DataTourKey | { raw: string };

export const resolveStepTarget = (target: StepTarget): string => (typeof target === "string" ? tourSelector(target) : target.raw);

export interface StepDemo {
  message?: string;
}

export interface TourStep {
  id: StepId;
  title: string;
  body: string;
  target: StepTarget;
  placement: StepPlacement;
  spotlightClicks: boolean;
  // Disables joyride's overlay click-shield
  overlayClickThrough?: boolean;
  // Replayed by the progress widget when the user opens this step out of order.
  prerequisites?: StepId[];
  demo?: StepDemo;
}

export interface MajorTaskEntry {
  route: (taskId: string) => string;
  // Wait for the user to arrive at the route rather than navigating immediately.
  advanceOnArrival?: boolean;
}

export interface MajorTask {
  id: MajorTaskId;
  label: string;
  sectionName: string;
  subtaskIds: StepId[];
  entry?: MajorTaskEntry;
}

export const STEPS: TourStep[] = [
  {
    id: STEP_IDS.OPEN_CHAT,
    title: "Open the AI assistant",
    body: "Click the chat icon in the bottom-right corner to open the demo agent.",
    target: "CHATBOT_FAB",
    placement: "left-end",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.SEND_MESSAGE,
    title: "Send a message",
    body: "Type a question and hit send. The demo agent will respond and generate a trace you can inspect.",
    target: "CHATBOT_PANEL",
    placement: "left",
    spotlightClicks: true,
    prerequisites: [STEP_IDS.OPEN_CHAT],
    demo: { message: "Hi! I'm trying out Arthur Engine!" },
  },
  {
    id: STEP_IDS.VIEW_TRACES,
    title: "Open the Observe view",
    body: "Every request to the agent is captured as a trace. Click 'Observe' in the sidebar to see them.",
    target: "NAV_TRACES",
    placement: "right",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.INSPECT_TRACE,
    title: "Open a trace",
    body: "Click any trace row to open its details.",
    target: "TRACES_TABLE",
    placement: "top",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.REVIEW_TRACE,
    title: "Review the details",
    body: "Look through the prompt, response, and eval scores in the side panel, then close it when you're ready.",
    target: "TRACE_DRAWER",
    placement: "left",
    spotlightClicks: true,
    overlayClickThrough: true,
    prerequisites: [STEP_IDS.INSPECT_TRACE],
  },
  {
    id: STEP_IDS.VIEW_DATASETS,
    title: "Open the Datasets view",
    body: "Datasets are the test sets used to evaluate prompts. Click 'Dataset' in the sidebar to see what's available.",
    target: "NAV_DATASETS",
    placement: "right",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.BROWSE_DATASETS,
    title: "Browse datasets",
    body: "These are the test sets used to evaluate prompts. Take a look around when you're ready, then click Next.",
    target: "DATASETS_TABLE",
    placement: "top",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.VIEW_PROMPTS,
    title: "Open the Prompts view",
    body: "Prompts are the templates that drive your task. Click 'Prompts' in the sidebar to see what's available.",
    target: "NAV_PROMPTS",
    placement: "right",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.EDIT_PROMPT,
    title: "Inspect a prompt",
    body: "Click any prompt row to open its detail view, where you can see versions, tags, and make edits.",
    target: "PROMPTS_TABLE",
    placement: "top",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.RUN_EXPERIMENT,
    title: "Open the experiment menu",
    body: "Experiments let you test prompt variations side-by-side against a dataset. Click 'Experiment' to get started.",
    target: "CREATE_EXPERIMENT_BUTTON",
    placement: "left-start",
    spotlightClicks: true,
  },
  {
    id: STEP_IDS.CHOOSE_EXPERIMENT_TYPE,
    title: "Pick a starting point",
    body: "Choose 'Create New' to start fresh, or 'Create from Existing' to clone an existing experiment.",
    target: { raw: ".MuiMenu-paper" },
    placement: "left",
    spotlightClicks: true,
    prerequisites: [STEP_IDS.RUN_EXPERIMENT],
  },
];

export const MAJOR_TASKS: MajorTask[] = [
  {
    id: MAJOR_TASK_IDS.CHAT,
    label: "Chat with the demo agent",
    sectionName: "Demo Agent",
    subtaskIds: [STEP_IDS.OPEN_CHAT, STEP_IDS.SEND_MESSAGE],
  },
  {
    id: MAJOR_TASK_IDS.OBSERVE,
    label: "Observe traces",
    sectionName: "Observe",
    subtaskIds: [STEP_IDS.VIEW_TRACES, STEP_IDS.INSPECT_TRACE, STEP_IDS.REVIEW_TRACE],
    entry: { route: tourRoutes.traces, advanceOnArrival: true },
  },
  {
    id: MAJOR_TASK_IDS.DATASETS,
    label: "Get familiar with datasets",
    sectionName: "Datasets",
    subtaskIds: [STEP_IDS.VIEW_DATASETS, STEP_IDS.BROWSE_DATASETS],
    entry: { route: tourRoutes.datasets, advanceOnArrival: true },
  },
  {
    id: MAJOR_TASK_IDS.PROMPTS,
    label: "Manage your prompts",
    sectionName: "Prompts",
    subtaskIds: [STEP_IDS.VIEW_PROMPTS, STEP_IDS.EDIT_PROMPT],
    entry: { route: tourRoutes.promptsManagement, advanceOnArrival: true },
  },
  {
    id: MAJOR_TASK_IDS.EXPERIMENTS,
    label: "Run an experiment",
    sectionName: "Experiments",
    subtaskIds: [STEP_IDS.RUN_EXPERIMENT, STEP_IDS.CHOOSE_EXPERIMENT_TYPE],
    entry: { route: tourRoutes.promptsExperiments },
  },
];

export const findStep = (id: StepId): TourStep | undefined => STEPS.find((s) => s.id === id);

export const getStepDemo = (id: StepId): StepDemo | undefined => findStep(id)?.demo;

export const findMajorTask = (id: MajorTaskId): MajorTask | undefined => MAJOR_TASKS.find((t) => t.id === id);

export const findMajorTaskForStep = (stepId: StepId): MajorTask | undefined => MAJOR_TASKS.find((t) => t.subtaskIds.includes(stepId));

export const getMajorTaskIndex = (id: MajorTaskId): number => MAJOR_TASKS.findIndex((t) => t.id === id);

export const getStepIndex = (id: StepId): number => STEPS.findIndex((s) => s.id === id);
