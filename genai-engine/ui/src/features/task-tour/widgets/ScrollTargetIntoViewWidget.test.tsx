import { render } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ScrollTargetIntoViewWidget } from "./ScrollTargetIntoViewWidget";

import { createTourEngine, TourProvider } from "@/features/tour";

// jsdom defaults: innerWidth 1024 × innerHeight 768.
function makeTarget(rect: Partial<DOMRect>): { element: HTMLElement; scrollIntoView: ReturnType<typeof vi.fn> } {
  const element = document.createElement("div");
  const scrollIntoView = vi.fn();
  element.scrollIntoView = scrollIntoView;
  element.getBoundingClientRect = () => rect as DOMRect;
  return { element, scrollIntoView };
}

function renderWidget() {
  const engine = createTourEngine({
    config: { id: "task-tour", sections: [{ id: "prompts", steps: [] }] },
  });
  render(
    <TourProvider tour={engine}>
      <ScrollTargetIntoViewWidget />
    </TourProvider>
  );
  return engine;
}

function emitTargetFound(engine: ReturnType<typeof createTourEngine>, element: Element) {
  act(() => {
    engine.bus.emit("target:found", { tourId: "task-tour", sectionId: "prompts", stepId: "review-playground-prompt", element });
  });
}

describe("ScrollTargetIntoViewWidget", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("scrolls a fully off-screen target into view", () => {
    const engine = renderWidget();
    const { element, scrollIntoView } = makeTarget({ left: 2000, right: 2400, top: 100, bottom: 500, width: 400, height: 400 });

    emitTargetFound(engine, element);

    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ block: "nearest", inline: "center" }));
  });

  it("centers a partially clipped target", () => {
    const engine = renderWidget();
    // Half off the right edge (right > 1024).
    const { element, scrollIntoView } = makeTarget({ left: 800, right: 1200, top: 100, bottom: 500, width: 400, height: 400 });

    emitTargetFound(engine, element);

    expect(scrollIntoView).toHaveBeenCalledTimes(1);
  });

  it("does nothing when the target is comfortably visible", () => {
    const engine = renderWidget();
    const { element, scrollIntoView } = makeTarget({ left: 100, right: 500, top: 100, bottom: 500, width: 400, height: 400 });

    emitTargetFound(engine, element);

    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it("scrolls a card clipped by a narrower scroll container even when its box is inside the viewport", () => {
    // Real-world case: the docked tour panel narrows <main>, so the overflow-x
    // card row ends at x=700 while the window is still 1024 wide. The card's box
    // extends to 1000 (inside the viewport) but past the row's right edge — the
    // old viewport-only check wrongly treated it as visible.
    const engine = renderWidget();
    const container = document.createElement("div");
    container.style.overflowX = "auto";
    container.getBoundingClientRect = () => ({ left: 0, top: 0, right: 700, bottom: 768, width: 700, height: 768 }) as DOMRect;
    document.body.appendChild(container);
    const { element, scrollIntoView } = makeTarget({ left: 600, right: 1000, top: 100, bottom: 500, width: 400, height: 400 });
    container.appendChild(element);

    emitTargetFound(engine, element);

    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    container.remove();
  });

  it("leaves a full-bleed target larger than the viewport alone", () => {
    const engine = renderWidget();
    // Spans the whole viewport (a panel), already intersecting — centering would jump the page.
    const { element, scrollIntoView } = makeTarget({ left: 0, right: 1024, top: 0, bottom: 768, width: 1024, height: 768 });

    emitTargetFound(engine, element);

    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it("re-checks occlusion after the scroll settles", () => {
    const engine = renderWidget();
    const recheckOcclusion = vi.spyOn(engine, "recheckOcclusion");
    const { element } = makeTarget({ left: 2000, right: 2400, top: 100, bottom: 500, width: 400, height: 400 });

    emitTargetFound(engine, element);
    expect(recheckOcclusion).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(recheckOcclusion).toHaveBeenCalledTimes(1);
  });
});
