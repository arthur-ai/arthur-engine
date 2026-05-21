import { generatePath } from "react-router-dom";

export function resolveStepRoute(route: string, routeParams?: Record<string, string>): string {
  if (!routeParams || Object.keys(routeParams).length === 0) {
    return route;
  }

  try {
    return generatePath(route, routeParams);
  } catch {
    return route;
  }
}
