import { useCallback } from "react";

import { ResumeFab } from "../components/ResumeFab";
import { getTaskTourStepLabel } from "../tour-config";

import {
  useTour,
  useTourPluginStore,
  type TourStatePlugin,
} from "@/features/tour";

export interface ResumeFabWidgetProps {
  /** State plugin used to read the persisted status + completed keys. */
  statePlugin: TourStatePlugin;
  /** Notifies the parent when the FAB rect changes so a docked panel can follow. */
  onAnchorRectChange?: (rect: DOMRect | null) => void;
  /** Set by the parent to true once the user has clicked Resume — the FAB stops pulsing then. */
  panelAnchoredToFab?: boolean;
}

/**
 * Floating action button shown while the persistence status is `dismissed`,
 * or while the panel has been docked next to the FAB after a manual resume.
 * Resuming routes through `engine.resume()` for paused tours, and
 * `engine.start({ position, resume: true })` for fully-stopped ones — but
 * only when there is an actual incomplete step to resume to. A finished
 * tour ignores the click; restarting an already-completed tour would
 * otherwise loop the engine back to section 0.
 */
export function ResumeFabWidget({ statePlugin, onAnchorRectChange, panelAnchoredToFab = false }: ResumeFabWidgetProps) {
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

  // Terminal states never show the FAB, regardless of the dock flag. v0's
  // bug was that a stale dock flag (set on initial `tour:start`) kept the
  // FAB visible after completion; a stray click then re-entered the tour at
  // section 0 because `resumePosition()` returns null when everything is
  // complete and `actions.start()` defaults to the first section.
  if (persistedStatus === "completed") return null;
  const visible = persistedStatus === "dismissed" || panelAnchoredToFab;
  if (!visible) return null;

  return (
    <ResumeFab
      label={label}
      attractAttention={persistedStatus === "dismissed"}
      onClick={handleClick}
      onAnchorRectChange={onAnchorRectChange}
    />
  );
}
