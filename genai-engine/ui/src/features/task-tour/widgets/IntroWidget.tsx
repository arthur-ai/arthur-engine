import { useCallback } from "react";

import { SectionIntroDialog } from "../components/SectionIntroDialog";
import { TASK_TOUR_SECTIONS } from "../data";

import { useTour } from "@/features/tour";

/**
 * Mounted whenever the engine is in the `intro` state. Drives the
 * section-intro modal directly off the engine — `acknowledgeIntroduction`
 * advances to the first step of the section (or jumps to the next section
 * for intro-only sections), and `dismiss` parks the tour at the FAB.
 */
export function IntroWidget() {
  const { state, actions } = useTour();
  const onStart = useCallback(() => actions.acknowledgeIntroduction(), [actions]);
  const onDismiss = useCallback(() => actions.dismiss(), [actions]);

  if (state.status !== "intro") return null;

  const section = TASK_TOUR_SECTIONS[state.sectionIndex];
  if (!section) return null;

  return (
    <SectionIntroDialog
      open
      section={section}
      sectionIndex={state.sectionIndex}
      onStart={onStart}
      onDismiss={onDismiss}
    />
  );
}
