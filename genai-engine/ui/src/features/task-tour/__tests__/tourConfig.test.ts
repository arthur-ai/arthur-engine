import { describe, expect, it } from "vitest";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS } from "../selectors";
import { buildTourConfig } from "../tour-config";
import { TASK_TOUR_ACTIONS } from "../tourActions";

describe("task tour config", () => {
  it("wires the demo-agent steps to the task chatbot route", () => {
    const config = buildTourConfig("task-id");
    const agentSection = config.sections.find((section) => section.id === "agent");
    const openDemoAgentStep = agentSection?.steps.find((step) => step.id === "open-demo-agent");
    const sendMessageStep = agentSection?.steps.find((step) => step.id === "send-message");

    expect(openDemoAgentStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/chatbot",
        params: { taskId: "task-id" },
      },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.demoAgentOpened }]),
    });
    expect(sendMessageStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/chatbot",
        params: { taskId: "task-id" },
      },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.demoAgentMessageSent }],
    });
  });

  it("pauses at section boundaries so users control when the next intro opens", () => {
    expect(buildTourConfig("task-id").sectionCompletion).toBe("pause");
  });

  it("uses an action-only composite target for the generate synthetic dataset step", () => {
    const config = buildTourConfig("task-id");
    const datasetsSection = config.sections.find((section) => section.id === "datasets");
    const generateSyntheticStep = datasetsSection?.steps.find((step) => step.id === "generate-synthetic");

    expect(generateSyntheticStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.datasetGenerateSynthetic },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.syntheticDataFinished }],
    });
  });

  it("breaks trace-to-dataset guidance into trace, actions, add action, and drawer save steps", () => {
    const config = buildTourConfig("task-id");
    const datasetsSection = config.sections.find((section) => section.id === "datasets");
    const openTracesStep = datasetsSection?.steps.find((step) => step.id === "open-traces-for-dataset");
    const openTraceStep = datasetsSection?.steps.find((step) => step.id === "open-trace-for-dataset");
    const reviewActionsStep = datasetsSection?.steps.find((step) => step.id === "review-trace-actions");
    const openAddToDatasetStep = datasetsSection?.steps.find((step) => step.id === "open-add-to-dataset");
    const saveTraceToDatasetStep = datasetsSection?.steps.find((step) => step.id === "save-trace-to-dataset");

    expect(openTracesStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.navObserve) },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.observeOpened }]),
    });
    expect(openTraceStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/traces",
        params: { taskId: "task-id" },
      },
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.tracesFirstRow },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.traceOpened }]),
    });
    expect(reviewActionsStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/traces",
        params: { taskId: "task-id" },
      },
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.traceActions },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(openAddToDatasetStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.traceAddToDatasetAction },
      advanceOn: expect.arrayContaining([{ type: "click" }, { type: "action", name: TASK_TOUR_ACTIONS.traceAddToDatasetOpened }]),
    });
    expect(saveTraceToDatasetStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.traceAddToDatasetDrawer },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.traceAddedToDataset }],
    });
  });

  it("wires evaluate results as a tab step followed by an action-only details composite", () => {
    const config = buildTourConfig("task-id");
    const evalsSection = config.sections.find((section) => section.id === "evals");
    const openResultsTabStep = evalsSection?.steps.find((step) => step.id === "open-results-tab");
    const reviewResultDetailsStep = evalsSection?.steps.find((step) => step.id === "review-result-details");

    expect(openResultsTabStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/evaluate",
        params: { taskId: "task-id" },
      },
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.evaluateResultsTab) },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.evaluateResultsOpened }]),
    });
    expect(reviewResultDetailsStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/evaluate",
        params: { taskId: "task-id" },
        search: { section: "results" },
      },
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.evaluateResultDetails },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.evaluateResultDetailsReviewed }],
    });
  });

  it("guides prompt playground entry and splits drafting into anchored popovers", () => {
    const config = buildTourConfig("task-id");
    const promptsSection = config.sections.find((section) => section.id === "prompts");
    const openInPlaygroundStep = promptsSection?.steps.find((step) => step.id === "open-in-playground");
    const addPromptStep = promptsSection?.steps.find((step) => step.id === "add-prompt-in-playground");
    const reviewPromptStep = promptsSection?.steps.find((step) => step.id === "review-playground-prompt");
    const reviewControlsStep = promptsSection?.steps.find((step) => step.id === "review-playground-controls");

    expect(openInPlaygroundStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.promptOpenInPlayground },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.promptOpenedInPlayground }],
    });
    expect(addPromptStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.playgroundAddPrompt) },
      advanceOn: expect.arrayContaining([{ type: "click" }]),
    });
    expect(addPromptStep?.route).toBeUndefined();
    expect(reviewPromptStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.playgroundPromptCard },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(reviewControlsStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.playgroundVariablesButton) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
  });

  it("guides create experiment through modal sections with action-only popovers", () => {
    const config = buildTourConfig("task-id");
    const promptsSection = config.sections.find((section) => section.id === "prompts");

    const openCreateStep = promptsSection?.steps.find((step) => step.id === "open-create-experiment");
    const infoStep = promptsSection?.steps.find((step) => step.id === "complete-experiment-info");
    const promptMappingStep = promptsSection?.steps.find((step) => step.id === "complete-prompt-mapping");
    const createExperimentStep = promptsSection?.steps.find((step) => step.id === "create-experiment");

    expect(openCreateStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/prompts",
        params: { taskId: "task-id" },
        search: { tab: "prompt-experiments" },
      },
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentEntry },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentModalOpened }],
    });

    expect(infoStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfo },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentInfoCompleted }],
      popover: { placement: "left" },
    });

    expect(promptMappingStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentPromptMappingsCompleted }],
      popover: { placement: "left" },
    });

    expect(createExperimentStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentFinal },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentCreated }],
      popover: { placement: "left" },
    });
  });

  it("routes deploy back to the prompt detail before production tagging", () => {
    const config = buildTourConfig("task-id");
    const deploySection = config.sections.find((section) => section.id === "deploy");
    const openProductionPromptStep = deploySection?.steps.find((step) => step.id === "open-production-prompt");
    const tagProductionStep = deploySection?.steps.find((step) => step.id === "tag-production");

    expect(openProductionPromptStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/prompts",
        params: { taskId: "task-id" },
        search: { tab: "prompts-management" },
      },
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.promptsFirstRow) },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.promptInspected }]),
    });
    expect(tagProductionStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.promptTags },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.promptPromoted }],
    });
  });
});
