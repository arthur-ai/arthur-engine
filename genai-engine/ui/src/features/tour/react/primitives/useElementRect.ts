import { useEffect, useState } from "react";

/**
 * Tracks an element's bounding client rect across resizes, scrolls, and
 * window size changes. Returns `null` when the element is detached or unset.
 */
export function useElementRect(element: Element | null): DOMRect | null {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!element) {
      setRect(null);
      return;
    }
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setRect(element.getBoundingClientRect()));
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(element);
    element.addEventListener("transitionend", update);
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      element.removeEventListener("transitionend", update);
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [element]);

  return rect;
}
