import { describe, expect, it, vi } from "vitest";

import { dispatchTourEvent, registerTaskTourActionBridge, TASK_TOUR_EVENTS } from "../tourActions";

describe("task-tour action bridge", () => {
  it("routes legacy dispatchTourEvent calls through the active engine bridge", () => {
    const bridge = vi.fn();
    const cleanup = registerTaskTourActionBridge(bridge);

    dispatchTourEvent(TASK_TOUR_EVENTS.traceOpened);
    cleanup();
    dispatchTourEvent(TASK_TOUR_EVENTS.traceOpened);

    expect(bridge).toHaveBeenCalledTimes(1);
    expect(bridge).toHaveBeenCalledWith(TASK_TOUR_EVENTS.traceOpened);
  });

  it("restores the previous bridge when nested registrations clean up", () => {
    const outer = vi.fn();
    const inner = vi.fn();
    const cleanupOuter = registerTaskTourActionBridge(outer);
    const cleanupInner = registerTaskTourActionBridge(inner);

    dispatchTourEvent(TASK_TOUR_EVENTS.traceOpened);
    cleanupInner();
    dispatchTourEvent(TASK_TOUR_EVENTS.traceOpened);
    cleanupOuter();

    expect(inner).toHaveBeenCalledTimes(1);
    expect(outer).toHaveBeenCalledTimes(1);
  });
});
