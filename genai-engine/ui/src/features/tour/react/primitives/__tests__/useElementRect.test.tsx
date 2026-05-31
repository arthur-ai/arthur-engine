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
  });

  it("remeasures when transform transitions finish", async () => {
    const element = document.createElement("div");
    let left = 8;
    element.getBoundingClientRect = () => new DOMRect(left, 12, 100, 40);

    const { result } = renderHook(() => useElementRect(element));

    await waitFor(() => expect(result.current?.left).toBe(8));

    left = 120;
    element.dispatchEvent(new TransitionEvent("transitionend", { bubbles: true, propertyName: "transform" }));

    await waitFor(() => expect(result.current?.left).toBe(120));
  });

  it("settles on the final rect after a transform-only entrance animation", async () => {
    // Simulates a Grow/scale entrance: the visual rect moves every frame
    // without ResizeObserver firing (transform doesn't resize the layout box)
    // and without a transitionend reaching this element's listener.
    const element = document.createElement("div");
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
