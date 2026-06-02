import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useElementRect } from "../useElementRect";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

/**
 * jsdom has no layout engine, so both `getBoundingClientRect` and
 * `getClientRects` must be stubbed. `rendered` toggles whether the element
 * generates layout boxes (`getClientRects().length > 0`) — the signal the hook
 * uses to decide a still-attached element is actually visible.
 */
function makeElement(getRect: () => DOMRect, rendered: () => boolean = () => true): HTMLElement {
  const element = document.createElement("div");
  element.getBoundingClientRect = getRect;
  element.getClientRects = (() => (rendered() ? [{} as DOMRect] : []) as unknown as DOMRectList) as Element["getClientRects"];
  document.body.appendChild(element);
  return element;
}

describe("useElementRect", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverStub);
    document.body.innerHTML = "";
  });

  it("returns null and installs no subscription when there is no element", () => {
    const { result } = renderHook(() => useElementRect(null));
    expect(result.current).toBeNull();
  });

  it("measures the element on mount", async () => {
    const element = makeElement(() => new DOMRect(8, 12, 100, 40));

    const { result } = renderHook(() => useElementRect(element));

    await waitFor(() => expect(result.current?.left).toBe(8));
  });

  it("tracks a positional shift when nothing resizes, scrolls, or transitions", async () => {
    let left = 10;
    const element = makeElement(() => new DOMRect(left, 0, 100, 40));

    const { result } = renderHook(() => useElementRect(element));
    await waitFor(() => expect(result.current?.left).toBe(10));

    // Surrounding layout pushes the element over — same node, new position, but
    // no resize / scroll / transition event fires to announce it. floating-ui's
    // per-frame poll is what catches it (this also covers MUI Grow/scale
    // entrances, which move via transform without resizing the layout box).
    left = 200;

    await waitFor(() => expect(result.current?.left).toBe(200));
  });

  it("settles on the final rect after a transform-only entrance animation", async () => {
    const lefts = [40, 64, 88, 110, 120, 120];
    let i = 0;
    const element = makeElement(() => {
      const left = lefts[Math.min(i, lefts.length - 1)];
      i += 1;
      return new DOMRect(left, 0, 100, 40);
    });

    const { result } = renderHook(() => useElementRect(element));

    await waitFor(() => expect(result.current?.left).toBe(120));
  });

  it("rebinds and remeasures when the tracked element identity changes", async () => {
    const a = makeElement(() => new DOMRect(1, 0, 10, 10));
    const b = makeElement(() => new DOMRect(2, 0, 10, 10));

    const { result, rerender } = renderHook(({ el }) => useElementRect(el), {
      initialProps: { el: a as Element | null },
    });
    await waitFor(() => expect(result.current?.x).toBe(1));

    rerender({ el: b });

    await waitFor(() => expect(result.current?.x).toBe(2));
  });

  it("clears the rect when the element prop goes back to null", async () => {
    const a = makeElement(() => new DOMRect(1, 0, 10, 10));

    const { result, rerender } = renderHook(({ el }) => useElementRect(el), {
      initialProps: { el: a as Element | null },
    });
    await waitFor(() => expect(result.current?.x).toBe(1));

    rerender({ el: null });

    await waitFor(() => expect(result.current).toBeNull());
  });

  it("returns a stable rect reference while measurements are unchanged", async () => {
    const element = makeElement(() => new DOMRect(3, 3, 3, 3));

    const { result } = renderHook(() => useElementRect(element));
    await waitFor(() => expect(result.current?.x).toBe(3));
    const first = result.current;

    // A no-op remeasure must not churn the reference, or every downstream
    // consumer (spotlight, popover) re-renders each frame.
    window.dispatchEvent(new Event("resize"));
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(result.current).toBe(first);
  });

  it("clears the rect once the tracked element detaches from the document", async () => {
    const element = makeElement(() => new DOMRect(8, 12, 100, 40));

    const { result } = renderHook(() => useElementRect(element));
    await waitFor(() => expect(result.current?.left).toBe(8));

    element.remove();
    window.dispatchEvent(new Event("resize"));

    await waitFor(() => expect(result.current).toBeNull());
  });

  it("clears the rect when a connected element collapses to no layout box", async () => {
    let rendered = true;
    const element = makeElement(
      () => new DOMRect(8, 12, 100, 40),
      () => rendered
    );

    const { result } = renderHook(() => useElementRect(element));
    await waitFor(() => expect(result.current?.width).toBe(100));

    // Still attached, but an ancestor sets display:none — no client rects. The
    // spotlight must clear rather than slam to the element's frozen rect.
    rendered = false;
    window.dispatchEvent(new Event("resize"));

    await waitFor(() => expect(result.current).toBeNull());
  });

  it("tears down the rAF loop on unmount", async () => {
    const cancelSpy = vi.spyOn(globalThis, "cancelAnimationFrame");
    const element = makeElement(() => new DOMRect(0, 0, 10, 10));

    const { unmount } = renderHook(() => useElementRect(element));
    await new Promise((resolve) => setTimeout(resolve, 25));
    unmount();

    expect(cancelSpy).toHaveBeenCalled();
    cancelSpy.mockRestore();
  });
});
