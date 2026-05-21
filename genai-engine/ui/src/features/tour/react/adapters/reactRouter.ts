import { useEffect, useMemo, useRef } from "react";
import { generatePath, useLocation, useNavigate } from "react-router-dom";

import { defaultResolveRoute } from "../../core/routes";
import type { ResolvedRoute, RouteSpec, TourLocation, TourNavigator } from "../../core/types";

/**
 * React Router 7 adapter for the tour engine. Uses `useNavigate` and
 * `useLocation`; `navigate(to)` resolves only after `location.pathname` (or
 * search/hash) has actually changed, so the engine's enter-step pipeline
 * doesn't proceed before the new page mounts.
 *
 * The adapter also delegates path-template resolution to React Router's
 * `generatePath`, so splats and optional segments work out of the box.
 */
export function useReactRouterNavigator(): TourNavigator {
  const navigate = useNavigate();
  const location = useLocation();
  const locRef = useRef<TourLocation>({
    pathname: location.pathname,
    search: location.search,
    hash: location.hash,
  });
  const waitersRef = useRef<Array<() => void>>([]);

  useEffect(() => {
    locRef.current = {
      pathname: location.pathname,
      search: location.search,
      hash: location.hash,
    };
    const queue = waitersRef.current;
    waitersRef.current = [];
    for (const resolve of queue) resolve();
  }, [location]);

  return useMemo<TourNavigator>(() => {
    const adapter: TourNavigator = {
      getLocation: () => locRef.current,
      navigate: (to) =>
        new Promise<void>((resolve) => {
          const cur = `${locRef.current.pathname}${locRef.current.search}${locRef.current.hash}`;
          if (cur === to) {
            resolve();
            return;
          }
          waitersRef.current.push(resolve);
          navigate(to);
        }),
      resolveRoute: (spec: RouteSpec): ResolvedRoute => {
        // Delegate to React Router's generatePath when params are provided.
        if (spec.params) {
          try {
            const pathname = generatePath(spec.path, spec.params as Record<string, string | null>);
            const base = defaultResolveRoute({ ...spec, path: pathname, params: undefined });
            return base;
          } catch {
            return defaultResolveRoute(spec);
          }
        }
        return defaultResolveRoute(spec);
      },
    };
    return adapter;
  }, [navigate]);
}
