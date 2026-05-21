import { Tour } from "../types";

import { OnboardingTourEvents } from "./events";

export const onboardingTour: Tour<OnboardingTourEvents> = {
  id: "onboarding",
  sections: [
    {
      id: "beginning",
      title: "Getting started",
      steps: [
        {
          type: "modal",
          id: "intro-adlc",
          route: "/tasks/:taskId/overview",
          title: "Welcome to your Arthur exercise",
          description:
            "This walkthrough follows the Agent Development Lifecycle (ADLC)—the flywheel Arthur uses to help teams ship reliable agents in production.",
          content:
            "You'll practice the same loop your team will use daily: observe behavior, measure quality with evals, and iterate until responses meet your standards.",
        },
        {
          type: "popover",
          id: "exercise-context",
          route: "/tasks/:taskId/overview",
          selector: "[data-tour-id='onboarding-task-content']",
          title: "Your exercise goal",
          description:
            "In this task, the agent is consistently responding outside of the readability parameters—responses are not at the quality we expect. Your job is to observe that behavior, interact with the demo agent, and set up evals to measure improvement.",
        },
      ],
    },
    {
      id: "agent",
      title: "Interacting with the agent",
      steps: [
        {
          type: "popover",
          id: "open-demo-agent",
          route: "/tasks/:taskId/overview",
          selector: "[data-tour-id='onboarding-chatbot-fab']",
          title: "Open the demo agent",
          description:
            "Click the Arthur AI Assistant in the corner. This demo agent is scoped to your task—it can answer questions about traces, prompts, datasets, and experiments while you explore.",
        },
        {
          type: "task",
          id: "chatbot-opened",
          route: "/tasks/:taskId/overview",
          selector: "[data-tour-id='onboarding-chatbot-fab']",
          title: "Open the assistant",
          description: "Click the chat button to open the demo agent.",
          waitFor: "onboarding:chatbot-opened",
        },
        {
          type: "popover",
          id: "chatbot-ready",
          route: "/tasks/:taskId/overview",
          selector: "[data-tour-id='onboarding-chatbot-drawer']",
          title: "Demo agent ready",
          description: "Great—the assistant is open. Next, send a message to see how the agent responds.",
        },
        {
          type: "task",
          id: "send-message",
          route: "/tasks/:taskId/overview",
          selector: "[data-tour-id='onboarding-chatbot-input']",
          title: "Send a message",
          description:
            "Type a prompt and press Send. Try something that would expose readability issues—for example, ask for a long, unstructured response.",
          waitFor: "onboarding:message-sent",
        },
      ],
    },
    {
      id: "evals",
      title: "Open evals",
      steps: [
        {
          type: "popover",
          id: "evals-nav",
          route: "/tasks/:taskId/evaluate",
          selector: "[data-tour-id='onboarding-sidebar-evaluate']",
          title: "Open Evaluate",
          description:
            "Evals are how you measure agent performance. Before fixing readability, you need a repeatable way to score responses—click Evaluate in the sidebar.",
        },
        {
          type: "popover",
          id: "evals-intro",
          route: "/tasks/:taskId/evaluate",
          selector: "[data-tour-id='onboarding-evaluate-header']",
          title: "What are evals?",
          description:
            "Evaluators are LLM-as-judge or rule-based checks that run against your agent outputs. Continuous evals track quality over time so you can see when readability drifts.",
        },
        {
          type: "popover",
          id: "evals-create",
          route: "/tasks/:taskId/evaluate",
          selector: "[data-tour-id='onboarding-evaluator-create']",
          title: "Create an evaluator",
          description:
            "Click Next, then open Evaluator, complete the form (template, instructions, model), and save. The tour continues automatically when you submit.",
        },
        {
          type: "task",
          id: "eval-modal",
          route: "/tasks/:taskId/evaluate",
          selector: "[data-tour-id='onboarding-evaluator-create']",
          title: "Create an evaluator",
          description: "Complete and submit the evaluator form.",
          waitFor: "onboarding:eval-submitted",
        },
      ],
    },
    {
      id: "traces",
      title: "Looking at traces",
      steps: [
        {
          type: "popover",
          id: "traces-nav",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-sidebar-traces']",
          title: "Open Observe",
          description:
            "Open the Observe view to see the trail of requests your agent generates. Each trace is one end-to-end interaction you can inspect.",
        },
        {
          type: "popover",
          id: "traces-header",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-traces-header']",
          title: "Traces overview",
          description:
            "Traces group spans—the individual steps your agent took. Use this view to find the interaction you just triggered with the demo agent.",
        },
        {
          type: "popover",
          id: "traces-table",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-traces-table']",
          title: "Trace list",
          description:
            "Each row is a trace. Columns show latency, token usage, cost, and eval annotations so you can spot quality issues quickly.",
        },
        {
          type: "popover",
          id: "traces-open-row",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-traces-table']",
          title: "Open a trace",
          description:
            "Press Next to open the most recent trace from the top (likely the chat you just sent). You can also click any row yourself.",
          advanceAction: "open-first-trace",
        },
        {
          type: "popover",
          id: "traces-drawer",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-trace-drawer']",
          title: "Inside a trace",
          description:
            "A trace is a tree of spans. Select spans to see inputs, outputs, latency, token counts, and cost—everything Arthur captured for debugging.",
        },
        {
          type: "popover",
          id: "traces-annotations",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-trace-annotations']",
          title: "Continuous eval annotations",
          description:
            "Continuous Evals run automatically on production traffic. Look for failures in the Readability Eval—these highlight responses outside your quality bar.",
        },
        {
          type: "popover",
          id: "traces-feedback",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-feedback-panel']",
          title: "Manual feedback",
          description:
            "Developers can leave human feedback here; apps can also send feedback via API. This ground truth helps tune evals and prioritize fixes.",
        },
        {
          type: "task",
          id: "traces-feedback-submit",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-feedback-panel']",
          title: "Submit feedback",
          description: "Leave a thumbs up/down and optional notes, then submit.",
          waitFor: "onboarding:feedback-submitted",
        },
      ],
    },
    {
      id: "datasets",
      title: "Working with datasets",
      steps: [
        {
          type: "popover",
          id: "datasets-nav",
          route: "/tasks/:taskId/datasets",
          selector: "[data-tour-id='onboarding-sidebar-datasets']",
          title: "Open Datasets",
          description:
            "Datasets are the test cases developers use to ship high-quality agent releases. Open Datasets to see what's available for this task.",
        },
        {
          type: "popover",
          id: "datasets-list",
          route: "/tasks/:taskId/datasets",
          selector: "[data-tour-id='onboarding-datasets-table']",
          title: "Dataset library",
          description: "Open the exercise dataset (typically the first row) to view curated test cases for this walkthrough.",
        },
        {
          type: "task",
          id: "datasets-open",
          route: "/tasks/:taskId/datasets",
          selector: "[data-tour-id='onboarding-datasets-table']",
          title: "Pre-loaded dataset",
          description: "Click the exercise dataset (typically the first row) to open it.",
          waitFor: "onboarding:dataset-detail-opened",
        },
        {
          type: "popover",
          id: "datasets-detail",
          route: "/tasks/:taskId/datasets/:datasetId",
          selector: "[data-tour-id='onboarding-dataset-table']",
          title: "Dataset rows",
          description: "Each row is a test case—prompts, expected behavior, or captured failures you want to prevent in production.",
        },
        {
          type: "popover",
          id: "datasets-add-from-traces",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-trace-drawer']",
          title: "Add trace to dataset",
          description:
            "Return to Observe and open your trace. Use Add to Dataset to capture this failure as a future regression test.",
        },
        {
          type: "task",
          id: "datasets-add-open",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='onboarding-add-to-dataset-drawer']",
          title: "Add to dataset workflow",
          description: "Open Add to Dataset from the trace actions, pick the exercise dataset, and save the row.",
          waitFor: "onboarding:trace-added-to-dataset",
        },
        {
          type: "popover",
          id: "datasets-row-added",
          route: "/tasks/:taskId/datasets/:datasetId",
          selector: "[data-tour-id='onboarding-dataset-table']",
          title: "New row added",
          description: "Re-open the dataset to confirm the trace was added—this is how teams build regression suites from production issues.",
        },
        {
          type: "popover",
          id: "datasets-synthetic",
          route: "/tasks/:taskId/datasets/:datasetId",
          selector: "[data-tour-id='onboarding-dataset-synthetic']",
          title: "Generate synthetic data (optional)",
          description:
            "You can enrich datasets with synthetic examples based on existing rows. Try generating 5–10 new rows to expand coverage.",
        },
      ],
    },
    {
      id: "prompts",
      title: "Experimenting with prompts",
      steps: [
        {
          type: "popover",
          id: "prompts-nav",
          route: "/tasks/:taskId/prompts",
          selector: "[data-tour-id='onboarding-sidebar-prompts']",
          title: "Open Prompts",
          description: "Prompts combine messages, variables, and a model—the building blocks you will tune to fix failing evals.",
        },
        {
          type: "popover",
          id: "prompts-list",
          route: "/tasks/:taskId/prompts",
          selector: "[data-tour-id='onboarding-prompts-tab']",
          title: "Prompt library",
          description: "Open the Prompts tab and select a prompt to inspect its structure.",
        },
        {
          type: "task",
          id: "prompts-open",
          route: "/tasks/:taskId/prompts",
          selector: "[data-tour-id='onboarding-prompts-table']",
          title: "Inspect a prompt",
          description: "Open any prompt from the list to see messages, variables, and model settings.",
          waitFor: "onboarding:prompt-detail-opened",
        },
        {
          type: "popover",
          id: "prompts-detail",
          route: "/tasks/:taskId/prompts/:promptName",
          selector: "[data-tour-id='onboarding-prompt-detail']",
          title: "Prompt anatomy",
          description:
            "System and user messages, template variables, and model choice work together. Small changes here can fix readability failures you saw in Observe.",
        },
        {
          type: "popover",
          id: "prompts-playground",
          route: "/tasks/:taskId/playgrounds/prompts",
          selector: "[data-tour-id='onboarding-playground-header']",
          title: "Prompt playground",
          description:
            "Use the playground to iterate quickly—edit system prompts, variables, and models, then compare outputs before running a full experiment.",
        },
        {
          type: "popover",
          id: "prompts-experiment-menu",
          route: "/tasks/:taskId/prompts",
          selector: "[data-tour-id='onboarding-experiment-menu']",
          title: "Run an experiment",
          description:
            "Switch to the Runs tab, open Experiment → Create New, complete the wizard, and submit. The tour continues when the experiment is created.",
        },
        {
          type: "task",
          id: "prompts-experiment-modal",
          route: "/tasks/:taskId/prompts",
          selector: "[data-tour-id='onboarding-experiment-menu']",
          title: "Configure the experiment",
          description: "Complete and submit the experiment wizard.",
          waitFor: "onboarding:experiment-created",
        },
      ],
    },
  ],
};
