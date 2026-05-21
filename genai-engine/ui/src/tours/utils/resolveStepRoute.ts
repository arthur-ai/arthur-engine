import { generatePath } from "react-router-dom";

const hasUnresolvedParams = (route: string) => /:[A-Za-z0-9_]+/.test(route);

export function resolveStepRoute(route: string, routeParams?: Record<string, string>): string | null {
  if (!hasUnresolvedParams(route)) {
    return route;
  }

  if (!routeParams || Object.keys(routeParams).length === 0) {
    return null;
  }

  try {
    const resolved = generatePath(route, routeParams);
    return hasUnresolvedParams(resolved) ? null : resolved;
  } catch {
    return null;
  }
}
