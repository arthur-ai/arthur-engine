import { useCallback } from "react";

import { ResumeFab } from "../components/ResumeFab";
import { getTaskTourStepLabel } from "../tour-config";

import { useTour, useTourPluginStore, type TourStatePlugin } from "@/features/tour";

export interface ResumeFabWidgetProps {
  /** State plugin used to read the persisted status + completed keys. */
  statePlugin: TourStatePlugin;
}

/**
 * Floating action button shown only while the tour is halted (persistence
 * status `dismissed`). Resuming routes through `engine.resume()` for paused
 * tours, and `engine.start({ position, resume: true })` for fully-stopped
 * ones — but only when there is an actual incomplete step to resume to. A
 * finished tour ignores the click; restarting an already-completed tour would
 * otherwise loop the engine back to section 0.
 */
export function ResumeFabWidget({ statePlugin }: ResumeFabWidgetProps) {
  const { state, actions, config } = useTour();
  const persistedStatus = useTourPluginStore(statePlugin, (s) => s.snapshot.status);

  const handleClick = useCallback(() => {
    if (state.status === "dismissed") {
      actions.resume();
      return;
    }
    // Engine is idle or has finished — start fresh at the first incomplete
    // step. If `resumePosition` returns null every step is already complete,
    // so a "resume" would silently loop back to section 0; treat it as a
    // no-op instead. The completion certificate is the canonical end state.
    const resumePosition = statePlugin.resumePosition(config);
    if (!resumePosition) return;
    actions.start({ position: resumePosition, resume: true });
  }, [actions, config, state, statePlugin]);

  const label = (() => {
    if (state.status === "step") return getTaskTourStepLabel(state.sectionId, state.stepId);
    if (state.status === "intro") return getTaskTourStepLabel(state.sectionId, undefined);
    const resume = statePlugin.resumePosition(config);
    return resume ? getTaskTourStepLabel(resume.sectionId, resume.stepId) : "Resume tour";
  })();

  // The FAB stands in for the tour only while it is halted; a running tour
  // shows the checklist instead. `completed` is handled by the same check —
  // a finished tour is not `dismissed`, so the FAB never reappears to loop the
  // engine back to section 0.
  if (persistedStatus !== "dismissed") return null;

  return <ResumeFab label={label} attractAttention onClick={handleClick} />;
}
