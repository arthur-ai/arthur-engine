import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { createTourEngine } from "../../../core/engine";
import type { TourConfig } from "../../../core/types";
import { TourProvider } from "../../TourProvider";
import { useActiveTarget } from "../useActiveTarget";

const config: TourConfig = {
  id: "tour",
  sections: [
    {
      id: "section-a",
      steps: [{ id: "shared", target: { kind: "element", resolve: () => document.body }, content: "A" }],
    },
    {
      id: "section-b",
      steps: [{ id: "shared", target: { kind: "element", resolve: () => document.body }, content: "B" }],
    },
  ],
};

describe("useActiveTarget", () => {
  it("tracks targets emitted before React observes the new step state", () => {
    const firstElement = document.createElement("button");
    const secondElement = document.createElement("button");
    const engine = createTourEngine({
      config: {
        id: "tour",
        sections: [
          {
            id: "main",
            steps: [
              { id: "one", target: { kind: "element", resolve: () => firstElement }, content: "One" },
              { id: "two", target: { kind: "element", resolve: () => secondElement }, content: "Two" },
            ],
          },
        ],
      },
    });

    const wrapper = ({ children }: { children: ReactNode }) => <TourProvider tour={engine}>{children}</TourProvider>;
    const { result } = renderHook(() => useActiveTarget(), { wrapper });

    act(() => {
      engine.store.getState().setState({
        status: "step",
        sectionId: "main",
        stepId: "one",
        sectionIndex: 0,
        stepIndex: 0,
        globalStepIndex: 0,
        totalSteps: 2,
      });
      engine.bus.emit("target:found", {
        tourId: "tour",
        sectionId: "main",
        stepId: "one",
        element: firstElement,
      });
    });

    expect(result.current).toBe(firstElement);

    act(() => {
      engine.store.getState().setState({
        status: "step",
        sectionId: "main",
        stepId: "two",
        sectionIndex: 0,
        stepIndex: 1,
        globalStepIndex: 1,
        totalSteps: 2,
      });
      engine.bus.emit("target:found", {
        tourId: "tour",
        sectionId: "main",
        stepId: "two",
        element: secondElement,
      });
    });

    expect(result.current).toBe(secondElement);
  });

  it("ignores target events for duplicate step ids in inactive sections", async () => {
    const engine = createTourEngine({ config });
    await engine.start();
    const inactiveElement = document.createElement("button");
    const activeElement = document.createElement("button");

    const wrapper = ({ children }: { children: ReactNode }) => <TourProvider tour={engine}>{children}</TourProvider>;
    const { result } = renderHook(() => useActiveTarget(), { wrapper });

    act(() => {
      engine.bus.emit("target:found", {
        tourId: "tour",
        sectionId: "section-b",
        stepId: "shared",
        element: inactiveElement,
      });
    });

    expect(result.current).toBeNull();

    act(() => {
      engine.bus.emit("target:found", {
        tourId: "tour",
        sectionId: "section-a",
        stepId: "shared",
        element: activeElement,
      });
    });

    expect(result.current).toBe(activeElement);
  });

  it("ignores target events emitted by other tour engines", async () => {
    const engine = createTourEngine({ config });
    await engine.start();
    const otherElement = document.createElement("button");

    const wrapper = ({ children }: { children: ReactNode }) => <TourProvider tour={engine}>{children}</TourProvider>;
    const { result } = renderHook(() => useActiveTarget(), { wrapper });

    act(() => {
      engine.bus.emit("target:found", {
        tourId: "other-tour",
        sectionId: "section-a",
        stepId: "shared",
        element: otherElement,
      });
    });

    expect(result.current).toBeNull();
  });
});
