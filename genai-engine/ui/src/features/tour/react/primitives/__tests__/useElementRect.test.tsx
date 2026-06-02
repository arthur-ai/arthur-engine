import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useElementRect } from "../useElementRect";

class ResizeObserverStub {
  observe() {}
  disconnect() {}
}

describe("useElementRect", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverStub);
    document.body.innerHTML = "";
  });

  it("remeasures when transform transitions finish", async () => {
    const element = document.createElement("div");
    document.body.appendChild(element);
    let left = 8;
    element.getBoundingClientRect = () => new DOMRect(left, 12, 100, 40);

    const { result } = renderHook(() => useElementRect(element));

    await waitFor(() => expect(result.current?.left).toBe(8));

    left = 120;
    element.dispatchEvent(new TransitionEvent("transitionend", { bubbles: true, propertyName: "transform" }));

    await waitFor(() => expect(result.current?.left).toBe(120));
  });

  it("clears the rect once the tracked element detaches from the document", async () => {
    const element = document.createElement("div");
    element.getBoundingClientRect = () => new DOMRect(8, 12, 100, 40);
    document.body.appendChild(element);

    const { result } = renderHook(() => useElementRect(element));
    await waitFor(() => expect(result.current?.left).toBe(8));

    element.remove();
    window.dispatchEvent(new Event("resize"));

    await waitFor(() => expect(result.current).toBeNull());
  });

  it("tracks a positional shift when nothing resizes, scrolls, or transitions", async () => {
    const element = document.createElement("div");
    document.body.appendChild(element);
    let left = 10;
    element.getBoundingClientRect = () => new DOMRect(left, 0, 100, 40);

    const { result } = renderHook(() => useElementRect(element));
    await waitFor(() => expect(result.current?.left).toBe(10));

    // Surrounding layout pushes the element over — same node, new position, but
    // no resize / scroll / transition event fires to announce it.
    left = 200;

    await waitFor(() => expect(result.current?.left).toBe(200));
  });

  it("settles on the final rect after a transform-only entrance animation", async () => {
    // Simulates a Grow/scale entrance: the visual rect moves every frame
    // without ResizeObserver firing (transform doesn't resize the layout box)
    // and without a transitionend reaching this element's listener.
    const element = document.createElement("div");
    document.body.appendChild(element);
    const lefts = [40, 64, 88, 110, 120, 120];
    let i = 0;
    element.getBoundingClientRect = () => {
      const left = lefts[Math.min(i, lefts.length - 1)];
      i += 1;
      return new DOMRect(left, 0, 100, 40);
    };

    const { result } = renderHook(() => useElementRect(element));

    await waitFor(() => expect(result.current?.left).toBe(120));
  });
});
