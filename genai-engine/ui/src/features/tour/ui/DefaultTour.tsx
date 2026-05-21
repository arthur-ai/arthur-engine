import { PopoverAnchor } from "../react/primitives/PopoverAnchor";
import { Spotlight } from "../react/primitives/Spotlight";
import { TargetTracker } from "../react/primitives/TargetTracker";
import { TourPortal } from "../react/primitives/TourPortal";
import { useTour } from "../react/useTour";

import { DefaultIntroDialog } from "./DefaultIntroDialog";
import { DefaultStepPopover } from "./DefaultStepPopover";

const SPOTLIGHT_Z_INDEX = 1499;
const POPOVER_Z_INDEX = 1500;

/**
 * Drop-in default UI for a tour. Renders the spotlight, the floating popover,
 * and (when applicable) the section introduction dialog. Render this anywhere
 * inside `<TourProvider>` — the portal mounts everything at `document.body`.
 *
 * Returns `null` whenever the tour isn't actively running, so it's safe to
 * mount unconditionally at the app root.
 */
export function DefaultTour() {
  const { state, activeStep, actions } = useTour();

  if (state.status !== "running" || !activeStep) return null;

  const introOpen = activeStep.introductionPending && Boolean(activeStep.section.introduction);

  return (
    <TourPortal>
      <DefaultIntroDialog open={introOpen} section={activeStep.section} actions={actions} />
      {!introOpen ? (
        <TargetTracker>
          {({ rect }) => (
            <>
              <Spotlight rect={rect} highlight={activeStep.step.highlight} style={{ zIndex: SPOTLIGHT_Z_INDEX }} />
              <PopoverAnchor rect={rect} placement={activeStep.step.placement} style={{ zIndex: POPOVER_Z_INDEX }}>
                <DefaultStepPopover activeStep={activeStep} actions={actions} />
              </PopoverAnchor>
            </>
          )}
        </TargetTracker>
      ) : null}
    </TourPortal>
  );
}
