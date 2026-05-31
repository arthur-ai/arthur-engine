import { useEffect } from "react";

import { useTour } from "./useTour";

export function QueryHookTargetRefresh() {
  const { state, activeStep, actions } = useTour();
  const target = activeStep?.step.target;

  useEffect(() => {
    if (state.status !== "step" || target?.kind !== "queryHook" || typeof MutationObserver === "undefined") return;

    let frame = 0;
    const scheduleRefresh = () => {
      if (typeof window === "undefined") return;
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => actions.refreshTarget());
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
