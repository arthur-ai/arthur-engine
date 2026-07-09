import { findElementByExactText, useRegisterQueryHook } from "@arthur/shared-components/tour";
import { useMemo } from "react";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS } from "../selectors";

import { makePreferredDataTourIdResolver } from "./resolvers";

/**
 * Lookup chain that resolves the first trace row in the Observe table.
 *
 * Addresses dogfood report P0 #1 (`task-tour-traces-first-row` never appears
 * on rows): the `@arthur/shared-components` table doesn't always forward
 * `getRowProps` to the DOM. The resolver tries:
 *
 *  1. The literal `data-tour-id` (works when the table wrapper does forward
 *     props — keeps the v0 path functional)
 *  2. Walks any `main` element looking for the first non-empty `tbody tr`.
 *
 * Resolved element is fed back to the engine via the `queryHook` target
 * kind, so the spotlight + click trigger snap to the actual rendered row.
 */
function resolveTracesFirstRow(): Element | null {
  const direct = document.querySelector(tourSelector(TOUR_IDS.tracesFirstRow));
  if (direct) return direct;
  const main = document.querySelector("main");
  return main?.querySelector("table tbody tr") ?? null;
}

/**
 * Drawer-anchor resolvers. Same approach: try the `data-tour-id` first, then
 * fall back to a stable DOM landmark inside the open drawer (MUI Drawer
 * exposes `role="presentation"` on the surface and the body region is the
 * topmost `[class*="MuiDrawer-paper"]`).
 *
 * Spans area sits inside the drawer body — we walk to the first element with
 * a span-tree heading or the first scrollable region. The fallbacks are
 * intentionally generous because v0's report flagged that the slot prop
 * just never lands on a DOM node in the shared package version.
 */
function findDrawerPaper(): Element | null {
  // MUI Drawer renders a `[role="presentation"]` wrapper around the surface.
  // We pick the most-recently-opened drawer paper (last in DOM order).
  const papers = document.querySelectorAll('[role="presentation"] .MuiDrawer-paper, .MuiDrawer-paper');
  return papers.length ? papers[papers.length - 1] : null;
}

function resolveTraceDrawerSpans(): Element | null {
  const direct = document.querySelector(tourSelector(TOUR_IDS.traceDrawerSpans));
  if (direct) return direct;
  const drawer = findDrawerPaper();
  if (!drawer) return null;
  // Prefer an explicit span-tree heading region, otherwise fall back to the
  // first scrollable column the drawer renders.
  return (
    drawer.querySelector('[data-slot="spans"]') ??
    drawer.querySelector('[aria-label*="span" i]') ??
    drawer.querySelector("[data-spans-root]") ??
    drawer
  );
}

/**
 * True when an element is on-screen enough to spotlight. The `Trace Actions`
 * dropdown ships from `@arthur/shared-components` as a Base UI `Menu` with
 * `keepMounted`, so its items stay in the DOM but the closed popup is `hidden` —
 * we must skip those until the user opens the menu. Deliberately avoids
 * `getClientRects()` (always empty in layout-less jsdom) so the same predicate
 * works in unit tests; it checks the `hidden` attribute and computed
 * display/visibility instead.
 */
function isSpotlightable(el: Element): boolean {
  if (!el.isConnected || el.closest("[hidden]")) return false;
  const style = window.getComputedStyle(el);
  return style.display !== "none" && style.visibility !== "hidden";
}

const ACTION_CONTROL_SELECTOR = "button, [role='button'], [role='menuitem']";

/** First visible button / menu item whose text matches `label`. */
function findVisibleControlByText(root: ParentNode, label: RegExp): Element | null {
  return Array.from(root.querySelectorAll(ACTION_CONTROL_SELECTOR)).find((el) => label.test(el.textContent ?? "") && isSpotlightable(el)) ?? null;
}

/**
 * The `Trace Actions` dropdown trigger lives inside `@arthur/shared-components`,
 * which exposes no slot to hang a `data-tour-id` on it, so we resolve it by its
 * button label. Falls back to the coarse drawer-body anchor when the trigger
 * label can't be matched.
 */
export function resolveTraceActionsTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.traceActions)) ??
    findElementByExactText("Trace Actions", { selector: "button", closestSelector: "button" }) ??
    document.querySelector(tourSelector(TOUR_IDS.traceDrawerAddToDataset))
  );
}

/**
 * `Add to Dataset` is a menu item inside the (closed-by-default) Trace Actions
 * dropdown. We only match it once the menu is open and the item is visible;
 * until then we fall back to the trigger so the spotlight sits on the button the
 * user must click to reveal it. `ActiveTargetRefresh` re-resolves on DOM
 * mutations, so the spotlight snaps from trigger → item the moment it opens.
 */
export function resolveTraceAddToDatasetActionTarget(): Element | null {
  const explicitAction = document.querySelector(tourSelector(TOUR_IDS.traceAddToDatasetAction));
  if (explicitAction) return explicitAction;
  const menuItem = findVisibleControlByText(document, /add\s+to\s+dataset/i);
  if (menuItem) return menuItem;
  return resolveTraceActionsTarget();
}

/**
 * The save step spotlights the whole Add-to-Dataset drawer surface — the cutout
 * covers the entire drawer so the form stays bright and fully usable while the
 * popover walks the user through pick-dataset → map-column → Add Row. Falls back
 * to the trigger if the drawer hasn't mounted yet.
 */
export function resolveTraceAddToDatasetDrawerTarget(): Element | null {
  return document.querySelector(tourSelector(TOUR_IDS.traceAddToDatasetDrawer)) ?? resolveTraceAddToDatasetActionTarget();
}

/**
 * Registers all task-tour queryHook resolvers in one place. Mounted once
 * under `<TourHost>` so the resolvers are available regardless of which
 * route the user is on — the engine consults the resolver at step-enter
 * time, which is always after preparation has run (and therefore after the
 * drawer / table is in the DOM).
 */
export function TracesTargetWidget() {
  const drawerEvals = useMemo(() => makePreferredDataTourIdResolver(TOUR_IDS.traceAnnotationsModal, TOUR_IDS.traceDrawerEvals), []);
  const drawerFeedback = useMemo(() => makePreferredDataTourIdResolver(TOUR_IDS.traceFeedbackPopover, TOUR_IDS.traceDrawerFeedback), []);

  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.tracesFirstRow, resolveTracesFirstRow);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceDrawerSpans, resolveTraceDrawerSpans);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceDrawerEvals, drawerEvals);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceDrawerFeedback, drawerFeedback);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceActions, resolveTraceActionsTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceAddToDatasetAction, resolveTraceAddToDatasetActionTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceAddToDatasetDrawer, resolveTraceAddToDatasetDrawerTarget);

  return null;
}
