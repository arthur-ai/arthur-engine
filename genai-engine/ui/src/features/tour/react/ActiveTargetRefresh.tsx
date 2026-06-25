import { useEffect } from "react";

import { useTour } from "./useTour";

/**
 * Keeps the active step's spotlight bound to the *current* target node by
 * re-resolving it on DOM mutations — for every target kind, not just
 * `queryHook`. A `selector` target otherwise resolves once on step-enter and is
 * never re-checked, so a stale node left behind by a route exit-animation (or a
 * list that re-renders and swaps the matched node) strands the spotlight on a
 * detached element. Re-resolving on each mutation lets the engine rebind to the
 * live node or emit `target:lost` when nothing matches.
 *
 * Cost is bounded: refreshes coalesce to one `requestAnimationFrame` per
 * mutation burst, the observer is only attached while a step is active, and
 * re-emitting an identical element is a no-op downstream (so the spotlight's own
 * re-renders cannot drive a feedback loop).
 *
 * The same mutation burst also drives an occlusion re-check (after the refresh,
 * so it tests the freshly-resolved element) — this is how a modal/panel the
 * user opens *after* the step started gets caught. Both ride the one rAF; the
 * only added cost is the occlusion hit-test's `elementFromPoint` calls.
 */
export function ActiveTargetRefresh() {
  const { state, activeStep, actions } = useTour();
  const target = activeStep?.step.target;

  useEffect(() => {
    if (state.status !== "step" || typeof MutationObserver === "undefined") return;

    let frame = 0;
    const scheduleRefresh = () => {
      if (typeof window === "undefined") return;
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        actions.refreshTarget();
        actions.recheckOcclusion();
      });
    };

    const observer = new MutationObserver(scheduleRefresh);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [actions, state.status, target]);

  return null;
}
