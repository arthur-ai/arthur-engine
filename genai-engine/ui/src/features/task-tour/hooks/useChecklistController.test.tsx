import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { TASK_TOUR_SECTIONS } from "../data";
import { introKey, itemKey } from "../progress";
import { TOUR_IDS } from "../selectors";
import { buildTourConfig } from "../tour-config";

import { useChecklistController } from "./useChecklistController";

import { createTour, createTourStatePlugin, TourProvider } from "@/features/tour";

function memStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  };
}

function setup() {
  const statePlugin = createTourStatePlugin({
    storageKey: "test-task-tour",
    storage: memStorage(),
    getKey: (event) => itemKey(event.sectionId, event.stepId),
  });
  const engine = createTour({ config: buildTourConfig("task-1"), plugins: [statePlugin] });
  const wrapper = ({ children }: { children: ReactNode }) => <TourProvider tour={engine}>{children}</TourProvider>;
  const view = renderHook(() => useChecklistController(statePlugin), { wrapper });
  return { engine, statePlugin, view };
}

describe("useChecklistController", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("reports exactly 100% progress once every section intro and step is recorded", () => {
    const { statePlugin, view } = setup();

    act(() => {
      for (const section of TASK_TOUR_SECTIONS) {
        statePlugin.markCompleted(introKey(section.id));
        for (const item of section.items) statePlugin.markCompleted(itemKey(section.id, item.id));
      }
    });

    expect(view.result.current.totalProgress).toBe(1);
  });

  it("toggling a non-active step only marks it; the engine stays on the active step", async () => {
    // Stub the first real step's target so the engine resolves it synchronously
    // (skips the awaitTarget wait) and settles on `status: "step"`.
    const trigger = document.createElement("button");
    trigger.setAttribute("data-tour-id", TOUR_IDS.navDemoAgent);
    trigger.getBoundingClientRect = () => new DOMRect(0, 0, 24, 24);
    document.body.appendChild(trigger);

    const { engine, statePlugin, view } = setup();

    await act(async () => {
      await engine.start();
    });
    // Walk through the intro-only section + section intros to the first step.
    for (let i = 0; i < TASK_TOUR_SECTIONS.length && engine.getState().status === "intro"; i++) {
      await act(async () => {
        await engine.acknowledgeIntroduction();
      });
    }

    expect(engine.getState().status).toBe("step");
    const sectionIndex = view.result.current.currentSectionIndex;
    const activeIndex = view.result.current.currentItemIndex;
    const section = TASK_TOUR_SECTIONS[sectionIndex];
    const nonActive = section.items[activeIndex === 0 ? 1 : 0];

    act(() => {
      view.result.current.onToggleItem(nonActive);
    });

    expect(statePlugin.getSnapshot().completed.has(itemKey(section.id, nonActive.id))).toBe(true);
    expect(engine.getState()).toMatchObject({ status: "step", stepId: section.items[activeIndex].id });
  });
});
