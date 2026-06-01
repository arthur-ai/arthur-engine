import type { ComponentType } from "react";

import type { TourState } from "../core/types";

import { useTourState } from "./useTour";

/**
 * Mounts `Component` only while `predicate(state)` is true. Canonical sugar
 * for "this widget should appear on completion / during a step / while
 * paused":
 *
 * ```tsx
 * const CertificateWidget = withTourActive(
 *   BaseCertificateDialog,
 *   (s) => s.status === "completed",
 * );
 * ```
 *
 * Wrap the result with `displayName` if you care about React DevTools.
 */
export function withTourActive<P extends object>(Component: ComponentType<P>, predicate: (state: TourState) => boolean): ComponentType<P> {
  function ActiveWrapper(props: P) {
    const state = useTourState();
    if (!predicate(state)) return null;
    return <Component {...props} />;
  }
  ActiveWrapper.displayName = `withTourActive(${Component.displayName ?? Component.name ?? "Component"})`;
  return ActiveWrapper;
}
