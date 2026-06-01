import type { ReactNode } from "react";

import { useActiveTarget } from "./useActiveTarget";
import { useElementRect } from "./useElementRect";

export interface TargetTrackerRenderArgs {
  element: Element | null;
  rect: DOMRect | null;
}

export interface TargetTrackerProps {
  children: (args: TargetTrackerRenderArgs) => ReactNode;
}

/**
 * Render-prop primitive that resolves the active target element and tracks
 * its bounding rect.
 */
export function TargetTracker({ children }: TargetTrackerProps) {
  const element = useActiveTarget();
  const rect = useElementRect(element);
  return <>{children({ element, rect })}</>;
}
