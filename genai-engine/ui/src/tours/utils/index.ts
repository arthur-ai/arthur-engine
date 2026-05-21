import { matchPath } from "react-router-dom";

import type { AnyTourEvents, TourStep } from "../types";

import { resolveStepRoute } from "./resolveStepRoute";

export function isStepOnCurrentRoute(step: TourStep<AnyTourEvents>, pathname: string, routeParams?: Record<string, string>) {
  const resolvedRoute = resolveStepRoute(step.route, step.routeParams ?? routeParams);
  return !!matchPath({ path: resolvedRoute, end: true }, pathname);
}

export { resolveStepRoute };
