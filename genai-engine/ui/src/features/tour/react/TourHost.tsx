import type { ReactNode } from "react";

import { PreparationRunner } from "./PreparationRunner";
import { TourPortal } from "./primitives/TourPortal";
import { QueryHookTargetRefresh } from "./QueryHookTargetRefresh";

export interface TourHostProps {
  /**
   * Optional explicit portal container. Defaults to a shared element appended
   * to `document.body` (see {@link TourPortal}).
   */
  container?: HTMLElement | null;
  children: ReactNode;
}

/**
 * Cross-cutting shell for tour widgets. `TourHost` does three things:
 *  1. Mounts `<PreparationRunner />` so any step's `prepare.key` can drive a
 *     registered preparation hook.
 *  2. Portals its widget children into `document.body` via `TourPortal`,
 *     keeping every overlay in the same stacking context.
 *  3. Acts as the canonical place to compose widgets — `IntroWidget`,
 *     `ChecklistWidget`, `SpotlightWidget`, etc. The engine doesn't know
 *     about widgets at all; consumers decide what to render.
 */
export function TourHost({ container, children }: TourHostProps) {
  return (
    <>
      <PreparationRunner />
      <QueryHookTargetRefresh />
      <TourPortal container={container}>{children}</TourPortal>
    </>
  );
}
