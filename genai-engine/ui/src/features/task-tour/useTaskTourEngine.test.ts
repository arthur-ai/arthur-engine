import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const trackMock = vi.hoisted(() => vi.fn());
const trackDynamicMock = vi.hoisted(() => vi.fn());
const createTourMock = vi.hoisted(() => vi.fn());

vi.mock("@/services/analytics", () => ({ track: trackMock, trackDynamic: trackDynamicMock }));

vi.mock("@arthur/shared-components/tour", () => ({
  createTour: createTourMock,
  createAnalyticsPlugin: vi.fn(() => ({ name: "analytics" })),
  createTourStatePlugin: vi.fn(() => ({
    name: "state",
    // "completed" so the auto-start effect short-circuits and never calls start().
    getSnapshot: () => ({ status: "completed", completed: new Set<string>() }),
    resumePosition: () => null,
  })),
  itemKey: (sectionId: string, stepId: string) => `${sectionId}.${stepId}`,
}));

vi.mock("./highlights", () => ({ createTaskTourHighlightsPlugin: vi.fn(() => ({ name: "highlights" })) }));
vi.mock("./tour-config", () => ({ buildTourConfig: vi.fn(() => ({ id: "task-tour-evals-101", sections: [] })) }));

import { useTaskTourEngine } from "./useTaskTourEngine";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useTaskTourEngine", () => {
  it("emits tour/error with phase 'init' when engine construction throws", () => {
    createTourMock.mockImplementation(() => {
      throw new Error("boom");
    });

    const { result } = renderHook(() => useTaskTourEngine({ taskId: "t1" }));

    expect(trackMock).toHaveBeenCalledWith("tour/error", { phase: "init", message: "boom" });
    expect(result.current.engine).toBeNull();
  });

  it("returns the engine and emits no error when construction succeeds", () => {
    const fakeEngine = { getState: () => ({ status: "idle" }), start: vi.fn(), destroy: vi.fn() };
    createTourMock.mockReturnValue(fakeEngine);

    const { result } = renderHook(() => useTaskTourEngine({ taskId: "t1" }));

    expect(result.current.engine).toBe(fakeEngine);
    expect(trackMock).not.toHaveBeenCalled();
  });
});
