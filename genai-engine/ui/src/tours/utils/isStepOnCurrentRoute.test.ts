import { describe, expect, it } from "vitest";

import { isStepOnCurrentRoute } from "./index";

describe("isStepOnCurrentRoute", () => {
  it("matches static routes", () => {
    expect(
      isStepOnCurrentRoute(
        {
          type: "popover",
          id: "welcome",
          route: "/",
          selector: "[data-tour-id='onboarding-welcome']",
          title: "Welcome",
          description: "Welcome",
        },
        "/"
      )
    ).toBe(true);
  });

  it("matches parameterized routes when params are provided", () => {
    expect(
      isStepOnCurrentRoute(
        {
          type: "popover",
          id: "traces",
          route: "/tasks/:taskId/traces",
          selector: "[data-tour-id='traces']",
          title: "Traces",
          description: "Traces",
        },
        "/tasks/task-1/traces",
        { taskId: "task-1" }
      )
    ).toBe(true);
  });

  it("matches route patterns without resolving every param", () => {
    expect(
      isStepOnCurrentRoute(
        {
          type: "popover",
          id: "dataset-detail",
          route: "/tasks/:taskId/datasets/:datasetId",
          selector: "[data-tour-id='dataset']",
          title: "Dataset",
          description: "Dataset",
        },
        "/tasks/task-1/datasets/ds-9"
      )
    ).toBe(true);
  });
});
