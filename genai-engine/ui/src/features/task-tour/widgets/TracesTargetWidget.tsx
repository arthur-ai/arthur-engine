import { useMemo } from "react";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS } from "../selectors";

import { useRegisterQueryHook } from "@/features/tour";

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
 * Construct a stable resolver bound to a single `data-tour-id` value. The
 * returned function is identity-stable across renders (it's a fresh closure
 * each call, but the caller pins it via `useMemo` below).
 */
function makeDataTourIdResolver(id: string): () => Element | null {
  return () => document.querySelector(tourSelector(id as never));
}

function makePreferredDataTourIdResolver(preferredId: string, fallbackId: string): () => Element | null {
  return () => document.querySelector(tourSelector(preferredId as never)) ?? document.querySelector(tourSelector(fallbackId as never));
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
  const drawerAddToDataset = useMemo(() => makeDataTourIdResolver(TOUR_IDS.traceDrawerAddToDataset), []);

  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.tracesFirstRow, resolveTracesFirstRow);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceDrawerSpans, resolveTraceDrawerSpans);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceDrawerEvals, drawerEvals);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceDrawerFeedback, drawerFeedback);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.traceDrawerAddToDataset, drawerAddToDataset);

  return null;
}
