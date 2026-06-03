import { render } from "@testing-library/react";
import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TracesTourCleanupWidget } from "./TracesTourCleanupWidget";

import { createTourEngine, TourProvider } from "@/features/tour";

const setDrawerTarget = vi.hoisted(() => vi.fn());

vi.mock("@/components/traces/hooks/useDrawerTarget", () => ({
  useDrawerTarget: () => [{ target: "trace", id: "trace-id" }, setDrawerTarget],
}));

describe("TracesTourCleanupWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("closes the trace drawer when the traces section completes", () => {
    const engine = createTourEngine({
      config: {
        id: "task-tour",
        sections: [{ id: "traces", steps: [] }],
      },
    });

    render(
      <TourProvider tour={engine}>
        <TracesTourCleanupWidget />
      </TourProvider>
    );

    act(() => {
      engine.bus.emit("section:complete", { tourId: "task-tour", sectionId: "traces", sectionIndex: 0 });
    });

    expect(setDrawerTarget).toHaveBeenCalledWith({ id: null });
  });

  it("ignores other section completions", () => {
    const engine = createTourEngine({
      config: {
        id: "task-tour",
        sections: [{ id: "datasets", steps: [] }],
      },
    });

    render(
      <TourProvider tour={engine}>
        <TracesTourCleanupWidget />
      </TourProvider>
    );

    act(() => {
      engine.bus.emit("section:complete", { tourId: "task-tour", sectionId: "datasets", sectionIndex: 0 });
    });

    expect(setDrawerTarget).not.toHaveBeenCalled();
  });
});
