import { useEffect, useState } from "react";

/**
 * How long to keep re-measuring after a change, to let entrance animations
 * settle. Covers MUI's default transition durations (~225-300ms) with margin.
 */
const SETTLE_DURATION_MS = 500;

function rectsEqual(a: DOMRect | null, b: DOMRect | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

/**
 * Tracks an element's bounding client rect across resizes, scrolls, and
 * window size changes. Returns `null` when the element is detached or unset.
 *
 * After every change it also runs a short requestAnimationFrame "settle" loop
 * that re-measures until the rect stops moving (or the window elapses). This is
 * what keeps the spotlight/popover glued to elements that enter via a
 * `transform` animation — e.g. MUI's Grow/scale transition on menus and
 * dialogs. `ResizeObserver` ignores transform changes (the layout box never
 * resizes) and a `transitionend` dispatched on an animating ancestor never
 * reaches a child listener, so without polling the rect would be captured
 * mid-animation and never corrected.
 */
export function useElementRect(element: Element | null): DOMRect | null {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!element) {
      setRect(null);
      return;
    }
    let frame = 0;
    let settleFrame = 0;

    const applyRect = (next: DOMRect) => {
      setRect((current) => (rectsEqual(current, next) ? current : next));
    };

    const settle = (deadline: number, previous: DOMRect) => {
      const next = element.getBoundingClientRect();
      const stable = rectsEqual(previous, next);
      if (!stable) applyRect(next);
      if (stable || performance.now() >= deadline) return;
      settleFrame = requestAnimationFrame(() => settle(deadline, next));
    };

    const update = () => {
      cancelAnimationFrame(frame);
      cancelAnimationFrame(settleFrame);
      frame = requestAnimationFrame(() => {
        const initial = element.getBoundingClientRect();
        applyRect(initial);
        settle(performance.now() + SETTLE_DURATION_MS, initial);
      });
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(element);
    element.addEventListener("transitionend", update);
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      cancelAnimationFrame(settleFrame);
      ro.disconnect();
      element.removeEventListener("transitionend", update);
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [element]);

  return rect;
}
