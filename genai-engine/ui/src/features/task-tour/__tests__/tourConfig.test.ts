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
      formPrefill: {
        targetId: TOUR_IDS.chatSendPlaceholder,
        value: "What is an AI Agent?",
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
      formPrefill: {
        targetId: TOUR_IDS.datasetGenerateSyntheticModal,
        values: {
          datasetPurpose: "Data for testing general-purpose wikipedia search agent",
          columnDescriptions: {
            query: "A general-purpose question for the Wikipedia search agent to answer.",
            response: "The expected answer from the Wikipedia search agent.",
            search_query: "The search term the agent passes to the Wikipedia search tool to find relevant articles.",
            search_results: "The list of matching Wikipedia article titles returned by the search tool.",
            fetch_query: "The article title the agent passes to the Wikipedia fetch tool to retrieve its summary.",
            fetch_results: "The article summary returned by the Wikipedia fetch tool.",
          },
          modelName: "gpt-5-nano",
        },
        mode: "empty-only",
      },
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
    // `Add to Dataset` lives inside the closed Trace Actions dropdown, so this
    // step is action-only: clicking the trigger opens the menu without
    // advancing; only the `traceAddToDatasetOpened` action (emitted once the
    // menu item is clicked) advances the step.
    expect(openAddToDatasetStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.traceAddToDatasetAction },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.traceAddToDatasetOpened }],
    });
    // Spotlights the whole drawer; the backdrop doesn't trap clicks so the form
    // and its portaled sub-dialogs stay usable while the popover instructs.
    expect(saveTraceToDatasetStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.traceAddToDatasetDrawer },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.traceAddedToDataset }],
      overlay: { blockInteraction: false },
    });
  });

  it("walks the dataset detail UI with manual popovers between opening the dataset and the trace detour", () => {
    const config = buildTourConfig("task-id");
    const datasetsSection = config.sections.find((section) => section.id === "datasets");

    const rowsStep = datasetsSection?.steps.find((step) => step.id === "review-dataset-rows");
    const columnsStep = datasetsSection?.steps.find((step) => step.id === "review-dataset-columns");
    const growStep = datasetsSection?.steps.find((step) => step.id === "review-dataset-grow");
    const versionsStep = datasetsSection?.steps.find((step) => step.id === "review-dataset-versions");
    const experimentsStep = datasetsSection?.steps.find((step) => step.id === "review-dataset-experiments");

    // Every beat is a static-selector spotlight that waits for an explicit
    // Next click. None carries a `route` — the prior step landed on the dynamic
    // /datasets/:datasetId URL and a static route would strip it.
    expect(rowsStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.datasetTable) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(rowsStep?.route).toBeUndefined();

    expect(columnsStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.datasetConfigureColumns) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(columnsStep?.route).toBeUndefined();

    expect(growStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.datasetDataActions) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(growStep?.route).toBeUndefined();

    expect(versionsStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.datasetVersions) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(versionsStep?.route).toBeUndefined();

    expect(experimentsStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.datasetExperiments) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(experimentsStep?.route).toBeUndefined();

    // The mini-tour sits between opening the dataset and the trace round-trip.
    const stepIds = datasetsSection?.steps.map((step) => step.id) ?? [];
    const start = stepIds.indexOf("open-preloaded-dataset");
    const end = stepIds.indexOf("open-traces-for-dataset");
    expect(stepIds.slice(start + 1, end)).toEqual([
      "review-dataset-rows",
      "review-dataset-columns",
      "review-dataset-grow",
      "review-dataset-versions",
      "review-dataset-experiments",
    ]);
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
    const inspectPromptStep = promptsSection?.steps.find((step) => step.id === "inspect-prompt");
    const openInPlaygroundStep = promptsSection?.steps.find((step) => step.id === "open-in-playground");
    const duplicatePromptStep = promptsSection?.steps.find((step) => step.id === "duplicate-prompt-in-playground");
    const reviewPromptStep = promptsSection?.steps.find((step) => step.id === "review-playground-prompt");
    const openVariablesStep = promptsSection?.steps.find((step) => step.id === "open-variables");
    const reviewControlsStep = promptsSection?.steps.find((step) => step.id === "review-playground-controls");
    const reviewNotebookStep = promptsSection?.steps.find((step) => step.id === "review-notebook");

    expect(inspectPromptStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.demoTaskPromptRow },
    });
    expect(openInPlaygroundStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.promptOpenInPlayground },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.promptOpenedInPlayground }],
    });
    expect(duplicatePromptStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.playgroundDuplicatePrompt) },
      advanceOn: expect.arrayContaining([{ type: "click" }]),
      popover: { placement: "left" },
    });
    expect(duplicatePromptStep?.route).toBeUndefined();
    expect(reviewPromptStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.playgroundPromptCard },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true },
    });
    expect(openVariablesStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.playgroundVariablesButton) },
      advanceOn: expect.arrayContaining([{ type: "click" }]),
      popover: { placement: "bottom" },
    });
    expect(openVariablesStep?.route).toBeUndefined();
    expect(reviewControlsStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.playgroundVariablesPanel) },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.playgroundVariablesReviewed }],
      popover: { placement: "left" },
    });
    expect(reviewNotebookStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.playgroundPanel) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, placement: "left" },
    });
    expect(reviewNotebookStep?.route).toBeUndefined();
  });

  it("guides create experiment through modal sections with action-only popovers", () => {
    const config = buildTourConfig("task-id");
    const promptsSection = config.sections.find((section) => section.id === "prompts");

    const openCreateStep = promptsSection?.steps.find((step) => step.id === "open-create-experiment");
    const infoNameStep = promptsSection?.steps.find((step) => step.id === "experiment-info-name");
    const infoVersionsStep = promptsSection?.steps.find((step) => step.id === "experiment-info-versions");
    const infoDatasetStep = promptsSection?.steps.find((step) => step.id === "experiment-info-dataset");
    const infoEvaluatorsStep = promptsSection?.steps.find((step) => step.id === "experiment-info-evaluators");
    const reviewInfoStep = promptsSection?.steps.find((step) => step.id === "review-experiment-info");
    const explainPromptMappingStep = promptsSection?.steps.find((step) => step.id === "explain-prompt-mapping");
    const promptMappingStep = promptsSection?.steps.find((step) => step.id === "complete-prompt-mapping");
    const explainEvalMappingStep = promptsSection?.steps.find((step) => step.id === "explain-eval-mapping");
    const createExperimentStep = promptsSection?.steps.find((step) => step.id === "create-experiment");

    expect(openCreateStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/prompts",
        params: { taskId: "task-id" },
        search: { tab: "prompt-experiments" },
      },
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentEntry },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentModalOpened }],
      // The entry beat spotlights a normal page button — keep the click trap.
      overlay: { blockInteraction: true },
    });

    // Each form step walks its sections via manual "Next" beats, then ends with
    // a whole-form "review" beat that advances on the real submit click (no Next
    // button). Every beat inside the modal disables the backdrop so the rest of
    // the form (and its portaled dropdowns) stays interactive.
    expect(infoNameStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfoName },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, placement: "left" },
      overlay: { blockInteraction: false },
    });
    expect(infoVersionsStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfoVersions },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, placement: "left" },
      overlay: { blockInteraction: false },
    });
    expect(infoDatasetStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfoDataset },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, placement: "left" },
      overlay: { blockInteraction: false },
    });
    // Evaluators now advances via Next like the other sections; the whole-form
    // review beat below is what hands off on the real submit.
    expect(infoEvaluatorsStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfoEvaluators },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, placement: "left" },
      overlay: { blockInteraction: false },
    });
    expect(reviewInfoStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfo },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentInfoCompleted }],
      popover: { placement: "left" },
      overlay: { blockInteraction: false },
    });
    // Review beats carry no popover Next button — only the submit action advances.
    expect(reviewInfoStep?.popover).not.toHaveProperty("showNext", true);

    expect(explainPromptMappingStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappingsList },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, placement: "left" },
      overlay: { blockInteraction: false },
    });
    expect(promptMappingStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentPromptMappingsCompleted }],
      popover: { placement: "left" },
      overlay: { blockInteraction: false },
    });

    // The eval beats only render when evaluators were selected, so both carry a
    // skipWhen predicate that auto-skips them when the task has no evals.
    expect(explainEvalMappingStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentEvalMappingsList },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, placement: "left" },
      overlay: { blockInteraction: false },
    });
    expect(explainEvalMappingStep?.skipWhen).toBeDefined();
    expect(createExperimentStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentFinal },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentCreated }],
      popover: { placement: "left" },
      overlay: { blockInteraction: false },
    });
    expect(createExperimentStep?.skipWhen).toBeDefined();
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
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.demoTaskPromptRow },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.promptInspected }]),
    });
    expect(tagProductionStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.promptTags },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.promptPromoted }],
    });
  });

  it("guides deploy back through the Demo Agent before verifying fresh evals", () => {
    const config = buildTourConfig("task-id");
    const deploySection = config.sections.find((section) => section.id === "deploy");
    const stepIds = deploySection?.steps.map((step) => step.id);
    const reopenDemoAgentStep = deploySection?.steps.find((step) => step.id === "reopen-demo-agent");
    const sendVerificationMessageStep = deploySection?.steps.find((step) => step.id === "send-verification-message");
    const reviewVerificationMessageStep = deploySection?.steps.find((step) => step.id === "review-verification-message");
    const verifyEvalStep = deploySection?.steps.find((step) => step.id === "verify-eval-passes");
    const reviewLatestTraceStep = deploySection?.steps.find((step) => step.id === "review-latest-trace");

    expect(stepIds).toEqual([
      "open-production-prompt",
      "tag-production",
      "reopen-demo-agent",
      "send-verification-message",
      "review-verification-message",
      "verify-eval-passes",
      "review-latest-trace",
    ]);
    expect(reopenDemoAgentStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/chatbot",
        params: { taskId: "task-id" },
      },
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.navDemoAgent) },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.demoAgentOpened }]),
    });
    expect(sendVerificationMessageStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/chatbot",
        params: { taskId: "task-id" },
      },
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.chatSendPlaceholder) },
      formPrefill: {
        targetId: TOUR_IDS.chatSendPlaceholder,
        value: "What is an AI Agent?",
      },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.demoAgentMessageSent }],
    });
    expect(reviewVerificationMessageStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.chatWindow) },
      advanceOn: [{ type: "manual" }],
      popover: { showNext: true, nextLabel: "Next" },
    });
    expect(reviewVerificationMessageStep?.route).toBeUndefined();
    expect(verifyEvalStep).toMatchObject({
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.navObserve) },
      advanceOn: expect.arrayContaining([{ type: "click" }, { type: "action", name: TASK_TOUR_ACTIONS.deployVerified }]),
    });
    expect(verifyEvalStep?.route).toBeUndefined();
    expect(reviewLatestTraceStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/traces",
        params: { taskId: "task-id" },
      },
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.tracesFirstRow },
      advanceOn: expect.arrayContaining([{ type: "action", name: TASK_TOUR_ACTIONS.traceOpened }]),
    });
  });
});
