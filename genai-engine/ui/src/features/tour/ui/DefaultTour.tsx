import { applyBackdropAction, BackdropBlocker, getHighlightPadding } from "../react/primitives/BackdropBlocker";
import { PopoverAnchor } from "../react/primitives/PopoverAnchor";
import { Spotlight } from "../react/primitives/Spotlight";
import { TargetTracker } from "../react/primitives/TargetTracker";
import { TourPortal } from "../react/primitives/TourPortal";
import { useTour } from "../react/useTour";

import { DefaultIntroDialog } from "./DefaultIntroDialog";
import { DefaultStepPopover } from "./DefaultStepPopover";

const SPOTLIGHT_Z_INDEX = 1499;
const BLOCKER_Z_INDEX = 1499;
const POPOVER_Z_INDEX = 1500;

/**
 * Drop-in default UI for a tour. Renders the spotlight, an optional
 * interaction-blocking overlay, the floating popover, and (when applicable)
 * the section introduction dialog. Render this anywhere inside
 * `<TourProvider>` — the portal mounts everything at `document.body`.
 *
 * Returns `null` whenever the tour isn't actively running, so it's safe to
 * mount unconditionally at the app root.
 */
export function DefaultTour() {
  const { state, activeStep, actions } = useTour();

  if (state.status !== "running" || !activeStep) return null;

  const introOpen = activeStep.introductionPending && Boolean(activeStep.section.introduction);
  const overlay = activeStep.step.overlay;
  const blockInteraction = overlay?.blockInteraction === true;
  const highlight = activeStep.step.highlight;
  const padding = getHighlightPadding(highlight);

  return (
    <TourPortal>
      <DefaultIntroDialog open={introOpen} section={activeStep.section} actions={actions} />
      {!introOpen ? (
        <TargetTracker>
          {({ rect }) => {
            // When the highlight is explicitly disabled, the blocker should
            // cover the entire viewport — pairing the visual flat backdrop
            // with a fully blocking interaction layer.
            const cutoutRect = highlight?.shape === "none" ? null : rect;
            const showBlocker = blockInteraction && (cutoutRect !== null || highlight?.shape === "none");
            return (
              <>
                <Spotlight rect={rect} highlight={highlight} backdropColor={overlay?.color} style={{ zIndex: SPOTLIGHT_Z_INDEX }} />
                {showBlocker ? (
                  <BackdropBlocker
                    cutoutRect={cutoutRect}
                    padding={padding}
                    onBackdropClick={() => applyBackdropAction(overlay?.onBackdropClick, actions)}
                    style={{ zIndex: BLOCKER_Z_INDEX }}
                  />
                ) : null}
                <PopoverAnchor rect={rect} placement={activeStep.step.placement} style={{ zIndex: POPOVER_Z_INDEX }}>
                  <DefaultStepPopover activeStep={activeStep} actions={actions} />
                </PopoverAnchor>
              </>
            );
          }}
        </TargetTracker>
      ) : null}
    </TourPortal>
  );
}
