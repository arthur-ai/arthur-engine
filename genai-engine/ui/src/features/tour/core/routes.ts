import type { ResolvedRoute, RouteSpec, SearchInput, TourLocation, TourNavigator } from "./types";

/**
 * Normalize a `route` field (string or RouteSpec) into a RouteSpec.
 * String shorthand is treated as a fully-formed URL relative to the origin.
 */
export function toRouteSpec(route: string | RouteSpec): RouteSpec {
  return typeof route === "string" ? parseStringRoute(route) : route;
}

/**
 * Parse a literal URL string into a RouteSpec. Uses URL with a synthetic base
 * since route strings are typically relative (e.g. "/tasks/abc?range=24h").
 */
function parseStringRoute(value: string): RouteSpec {
  // Reserve "://" detection for absolute URLs; otherwise treat as relative.
  const base = "http://__tour_base__";
  let url: URL;
  try {
    url = new URL(value, base);
  } catch {
    return { path: value };
  }

  const isAbsolute = !value.startsWith("/") && /^[a-z][a-z0-9+.-]*:/i.test(value);
  const pathname = isAbsolute ? url.toString() : url.pathname;

  const spec: RouteSpec = { path: pathname };
  if (url.search) spec.search = url.search;
  if (url.hash) spec.hash = url.hash;
  return spec;
}

/**
 * Default route resolution. The engine uses this when the navigator does not
 * supply a `resolveRoute` override.
 */
export function defaultResolveRoute(spec: RouteSpec): ResolvedRoute {
  const pathname = applyPathParams(spec.path, spec.params);
  const search = serializeSearch(spec.search);
  const hash = normalizeHash(spec.hash);
  return { pathname, search, hash, full: `${pathname}${search}${hash}` };
}

/**
 * Default match: the user is "already on" the target if pathname matches and any
 * declared search/hash also matches. Undeclared search/hash are ignored.
 */
export function defaultMatchesRoute(resolved: ResolvedRoute, current: TourLocation): boolean {
  if (resolved.pathname !== current.pathname) return false;
  if (resolved.search && resolved.search !== current.search) return false;
  if (resolved.hash && resolved.hash !== current.hash) return false;
  return true;
}

export function resolveRouteWith(navigator: TourNavigator, spec: RouteSpec): ResolvedRoute {
  return navigator.resolveRoute ? navigator.resolveRoute(spec) : defaultResolveRoute(spec);
}

export function matchesRouteWith(navigator: TourNavigator, spec: RouteSpec, resolved: ResolvedRoute): boolean {
  if (spec.match) return spec.match(resolved, navigator.getLocation());
  if (navigator.matches) return navigator.matches(resolved, navigator.getLocation());
  return defaultMatchesRoute(resolved, navigator.getLocation());
}

function applyPathParams(path: string, params?: Record<string, string | number>): string {
  if (!params) return path;
  return path.replace(/:([A-Za-z_][A-Za-z0-9_]*)/g, (_match, name: string) => {
    const value = params[name];
    if (value === undefined) return `:${name}`;
    return encodeURIComponent(String(value));
  });
}

function serializeSearch(input: SearchInput | undefined): string {
  if (!input) return "";
  if (typeof input === "string") {
    if (input === "" || input === "?") return "";
    return input.startsWith("?") ? input : `?${input}`;
  }
  if (input instanceof URLSearchParams) {
    const str = input.toString();
    return str ? `?${str}` : "";
  }
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (value === null || value === undefined) continue;
    params.append(key, String(value));
  }
  const str = params.toString();
  return str ? `?${str}` : "";
}

function normalizeHash(input: string | undefined): string {
  if (!input) return "";
  return input.startsWith("#") ? input : `#${input}`;
}
