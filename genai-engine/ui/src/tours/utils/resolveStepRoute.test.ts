import { describe, expect, it } from "vitest";

import { resolveStepRoute } from "./resolveStepRoute";

describe("resolveStepRoute", () => {
  it("returns the route unchanged when no params are provided", () => {
    expect(resolveStepRoute("/tasks")).toBe("/tasks");
  });

  it("substitutes route params using react-router generatePath", () => {
    expect(resolveStepRoute("/tasks/:taskId/traces", { taskId: "abc-123" })).toBe("/tasks/abc-123/traces");
  });

  it("falls back to the template route when params are invalid", () => {
    expect(resolveStepRoute("/tasks/:taskId", {})).toBe("/tasks/:taskId");
  });
});
