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
});
