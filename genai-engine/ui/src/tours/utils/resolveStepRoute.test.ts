import { describe, expect, it } from "vitest";

import { resolveStepRoute } from "./resolveStepRoute";

describe("resolveStepRoute", () => {
  it("returns the route unchanged when it has no params", () => {
    expect(resolveStepRoute("/tasks")).toBe("/tasks");
  });

  it("substitutes route params using react-router generatePath", () => {
    expect(resolveStepRoute("/tasks/:taskId/traces", { taskId: "abc-123" })).toBe("/tasks/abc-123/traces");
  });

  it("returns null when params are missing for a parameterized route", () => {
    expect(resolveStepRoute("/tasks/:taskId", {})).toBeNull();
    expect(resolveStepRoute("/tasks/:taskId/overview", undefined)).toBeNull();
  });
});
