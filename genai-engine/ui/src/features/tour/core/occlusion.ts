/**
 * Occlusion detection for tour targets.
 *
 * The engine resolves a target element and renders a spotlight at its rect, but
 * it can't tell whether that element is actually *visible* — a modal or panel
 * the user opened can sit on top of it. This headless utility hit-tests the
 * target with `document.elementFromPoint` to decide whether it's the topmost
 * interactive surface, ignoring the tour's own overlay DOM (which is portaled
 * under a single `#tour-portal-root` host and would otherwise always win the
 * hit test). Distinguishes "covered by another element" (occlusion → recover)
 * from "scrolled out of view" (off-screen → not occlusion).
 */

export type OcclusionReason = "ok" | "covered" | "offscreen" | "indeterminate";

export interface OcclusionResult {
  occluded: boolean;
  /** The element sitting on top when occluded; null otherwise / indeterminate. */
  occluder: Element | null;
  reason: OcclusionReason;
}

export interface OcclusionOptions {
  /** Fraction of sampled points that must hit the target to count as visible. Default 0.5. */
  minVisibleRatio?: number;
  /** CSS selector for tour-owned DOM to ignore in the hit test. Default `#tour-portal-root`. */
  tourRootSelector?: string;
}

const DEFAULT_TOUR_ROOT_SELECTOR = "#tour-portal-root";
const DEFAULT_MIN_VISIBLE_RATIO = 0.5;
const NOT_OCCLUDED = (reason: OcclusionReason): OcclusionResult => ({ occluded: false, occluder: null, reason });

function canHitTest(): boolean {
  return typeof document !== "undefined" && typeof document.elementFromPoint === "function";
}

/**
 * Resolve the topmost NON-tour element at a viewport point. When the immediate
 * hit is inside the tour overlay (`tourRootSelector`), peel through the stack
 * with `elementsFromPoint` (front-to-back) and return the first element that
 * isn't tour-owned — robust against any number of stacked tour layers and any
 * z-index / pointer-events configuration.
 */
function topmostNonTourElement(x: number, y: number, tourRootSelector: string): Element | null {
  const direct = document.elementFromPoint(x, y);
  if (!direct) return null;
  if (!direct.closest(tourRootSelector)) return direct;
  const stack = typeof document.elementsFromPoint === "function" ? document.elementsFromPoint(x, y) : [direct];
  for (const el of stack) {
    if (!el.closest(tourRootSelector)) return el;
  }
  return null;
}

/** A point "shows" the target when the hit is the target, a descendant of it, or an ancestor box wrapping it. */
function pointShowsTarget(hit: Element, target: Element): boolean {
  return hit === target || target.contains(hit) || hit.contains(target);
}

/**
 * Determine whether `target` (at `rect`) is the topmost visible element, or is
 * covered by something on top. Returns `offscreen` (not occlusion) when the
 * rect has no viewport intersection — that's a scroll concern, not a cover —
 * and `indeterminate` when hit-testing is unavailable (SSR / jsdom) so callers
 * never act on a false positive.
 */
export function detectOcclusion(target: Element, rect: DOMRect, options: OcclusionOptions = {}): OcclusionResult {
  if (!canHitTest()) return NOT_OCCLUDED("indeterminate");

  const tourRootSelector = options.tourRootSelector ?? DEFAULT_TOUR_ROOT_SELECTOR;
  const minVisibleRatio = options.minVisibleRatio ?? DEFAULT_MIN_VISIBLE_RATIO;

  const viewportW = window.innerWidth || document.documentElement.clientWidth;
  const viewportH = window.innerHeight || document.documentElement.clientHeight;

  // Visible intersection of the rect with the viewport. Sample inside it so a
  // partially-scrolled target is probed where it's actually on screen.
  const left = Math.max(rect.left, 0);
  const top = Math.max(rect.top, 0);
  const right = Math.min(rect.right, viewportW);
  const bottom = Math.min(rect.bottom, viewportH);
  const width = right - left;
  const height = bottom - top;
  if (width <= 1 || height <= 1) return NOT_OCCLUDED("offscreen");

  // Center first (index 0) + four inset quarter points.
  const points: Array<[number, number]> = [
    [left + width / 2, top + height / 2],
    [left + width * 0.25, top + height * 0.25],
    [left + width * 0.75, top + height * 0.25],
    [left + width * 0.25, top + height * 0.75],
    [left + width * 0.75, top + height * 0.75],
  ];

  let sampled = 0;
  let visible = 0;
  let centerOccluder: Element | null = null;
  let firstOccluder: Element | null = null;

  points.forEach(([x, y], index) => {
    const hit = topmostNonTourElement(x, y, tourRootSelector);
    if (!hit) return; // indeterminate point — skip
    sampled += 1;
    if (pointShowsTarget(hit, target)) {
      visible += 1;
      return;
    }
    if (index === 0) centerOccluder = hit;
    if (!firstOccluder) firstOccluder = hit;
  });

  if (sampled === 0) return NOT_OCCLUDED("indeterminate");
  if (visible / sampled >= minVisibleRatio) return NOT_OCCLUDED("ok");
  return { occluded: true, occluder: centerOccluder ?? firstOccluder, reason: "covered" };
}

/**
 * Stable, analytics-safe identifier for an occluding element: prefers a
 * `data-tour-id`, then role/aria-label, then a short `tag#id.class` chain.
 * Never returns the DOM node itself (events forward only primitives).
 */
export function describeOccluder(el: Element | null): string {
  if (!el) return "unknown";
  const tourId = el.getAttribute("data-tour-id");
  if (tourId) return `data-tour-id=${tourId}`;
  const role = el.getAttribute("role");
  const label = el.getAttribute("aria-label");
  if (role || label) return [role && `role=${role}`, label && `label=${label}`].filter(Boolean).join(" ");
  const tag = el.tagName.toLowerCase();
  const id = el.id ? `#${el.id}` : "";
  const cls = el.classList.length > 0 ? `.${el.classList[0]}` : "";
  return `${tag}${id}${cls}`.slice(0, 120);
}
