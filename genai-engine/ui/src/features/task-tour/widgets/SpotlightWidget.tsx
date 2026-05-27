import {
  applyBackdropAction,
  BackdropBlocker,
  getHighlightPadding,
  Spotlight,
  TargetTracker,
  useTour,
  useTourLayer,
} from "@/features/tour";

/**
 * Renders the task tour's brand spotlight + interaction blocker around the
 * active step's target. Lives inside `TourHost`'s portal subtree, so its
 * fixed-position SVG and blocker panels share the same stacking context as
 * the checklist panel.
 *
 * When the target hasn't resolved we suppress the entire spotlight — the
 * checklist panel surfaces the instruction and the page stays usable until
 * the target appears.
 */
export function SpotlightWidget() {
  const { state, activeStep, actions } = useTour();
  const spotlightZ = useTourLayer("spotlight");
  const blockerZ = useTourLayer("blocker");

  if (state.status !== "step" || !activeStep) return null;

  const overlay = activeStep.step.overlay;
  const showBlocker = overlay?.blockInteraction === true;

  return (
    <TargetTracker>
      {({ rect }) => {
        if (!rect) return null;
        return (
          <>
            <Spotlight
              rect={rect}
              highlight={activeStep.step.highlight}
              backdropColor={overlay?.color ?? "rgba(15, 23, 42, 0.28)"}
              style={{ zIndex: spotlightZ }}
            />
            {showBlocker ? (
              <BackdropBlocker
                cutoutRect={rect}
                padding={getHighlightPadding(activeStep.step.highlight)}
                onBackdropClick={() => applyBackdropAction(overlay?.onBackdropClick, actions)}
                style={{ zIndex: blockerZ }}
              />
            ) : null}
          </>
        );
      }}
    </TargetTracker>
  );
}
