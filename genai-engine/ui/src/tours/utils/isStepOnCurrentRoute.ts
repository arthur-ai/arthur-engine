import { matchPath } from "react-router-dom";

import type { AnyTourEvents, TourStep } from "../types";

import { resolveStepRoute } from "./resolveStepRoute";

export function isStepOnCurrentRoute(step: TourStep<AnyTourEvents>, pathname: string, routeParams?: Record<string, string>) {
  const params = { ...routeParams, ...step.routeParams };
  const resolvedRoute = resolveStepRoute(step.route, params);

  if (resolvedRoute) {
    return !!matchPath({ path: resolvedRoute, end: true }, pathname);
  }

  return !!matchPath({ path: step.route, end: true }, pathname);
}
