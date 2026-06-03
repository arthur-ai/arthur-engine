import { autoUpdate } from "@floating-ui/react";
import { useEffect, useState } from "react";

function rectsEqual(a: DOMRect | null, b: DOMRect | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

/**
 * Tracks an element's bounding client rect and keeps it current. Returns `null`
 * when the element is detached or unset.
 *
 * Positioning is delegated to floating-ui's `autoUpdate`, the same engine the
 * step popover uses. With `animationFrame: true` it re-measures on scroll,
 * ancestor resize, the element's own resize, layout shifts, AND arbitrary
 * positional moves driven by surrounding layout (content loading above the
 * target, a sibling expanding) — the last of which `ResizeObserver` alone
 * misses because the element's own box never changes size. This also covers the
 * `transform` entrance animations (MUI Grow/scale) that the previous bespoke
 * settle loop existed to handle.
 */
export function useElementRect(element: Element | null): DOMRect | null {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!element) {
      setRect(null);
      return;
    }

    const update = () => {
      // Clear (rather than report a frozen / zeroed rect that strands the
      // spotlight) when the element is gone or no longer renders a box:
      //   - detached: navigation unmounts it, or a list re-renders and swaps it;
      //   - collapsed-but-attached: an ancestor sets display:none, or it is
      //     mid-exit-animation — `getBoundingClientRect` would read (0,0,0,0)
      //     and slam the spotlight to the top-left corner.
      // `getClientRects().length` is the "generates a layout box" signal: it is
      // 0 only for display:none / detached, while a `transform: scale(0)`
      // entrance (MUI Grow) still has length 1 — so this does not flicker
      // entrance animations. The engine's target re-resolution then rebinds to
      // the live node or emits target:lost.
      if (!element.isConnected || element.getClientRects().length === 0) {
        setRect(null);
        return;
      }
      const next = element.getBoundingClientRect();
      setRect((current) => (rectsEqual(current, next) ? current : next));
    };

    // `autoUpdate` invokes `update` once synchronously on setup, then on every
    // tracked change. A detached throwaway element satisfies the (reference,
    // floating) signature; only the reference's rect drives our measurement.
    const floating = document.createElement("div");
    return autoUpdate(element, floating, update, { animationFrame: true });
  }, [element]);

  return rect;
}
