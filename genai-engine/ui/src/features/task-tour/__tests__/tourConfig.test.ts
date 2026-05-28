import { describe, expect, it } from "vitest";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
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
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.syntheticDataGenerated }],
    });
  });
});
