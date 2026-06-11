import { parseAsString, useQueryState } from "nuqs";
import { useMemo, useRef } from "react";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { TASK_TOUR_OCCLUDERS } from "../occluders";
import { TOUR_IDS, tourSelector } from "../selectors";

import { makeDataTourIdResolver, makePreferredDataTourIdResolver } from "./resolvers";

import { type OccluderDescriptor, useRegisterOccluder, useRegisterQueryHook } from "@/features/tour";

/**
 * True when the Annotation Details dialog is actually rendered, detected by the
 * presence of its `data-tour-id` element (MUI unmounts a closed Dialog). We key
 * off the dialog's own DOM marker — the same anchor the tour's target resolver
 * uses for it — rather than a route/URL heuristic, so this can't silently break
 * if the Evaluate route is renamed or another route ever ends in `/evaluate`,
 * and it scopes to "the dialog exists" instead of the `?id` param it shares with
 * the trace drawer. `close()` still clears `?id`, the dialog's own close lever.
 */
export function isEvaluateResultsDetailsOpen(): boolean {
  return typeof document !== "undefined" && document.querySelector(tourSelector(TOUR_IDS.evaluateResultsDetailsDialog)) !== null;
}

/**
 * Registers Evaluate-page composite targets. Results detail starts on the
 * first results row, then retargets to the details dialog once it opens.
 *
 * The evaluator-detail hooks back the "Review an evaluator" mini-tour: after
 * the user maximizes an evaluator, these resolvers poll for the version
 * drawer, instructions panel, and judge-model field on the full-screen detail
 * view (which mount asynchronously once the eval data loads).
 *
 * Also registers the Annotation Details dialog as a close-only occluder so
 * `reconcileSurfaces` dismisses it on entering any step that doesn't declare it
 * open (e.g. `traces / open-observe`, whose Observe-nav target it would
 * otherwise cover). The dialog is purely `?id`-driven, so closing just clears
 * that param — the same lever its own Close button uses.
 */
export function EvaluateTargetWidget() {
  const resultDetails = useMemo(() => makePreferredDataTourIdResolver(TOUR_IDS.evaluateResultsDetailsDialog, TOUR_IDS.evaluateResultsFirstRow), []);
  const detailVersions = useMemo(() => makeDataTourIdResolver(TOUR_IDS.evaluatorDetailVersions), []);
  const detailInstructions = useMemo(() => makeDataTourIdResolver(TOUR_IDS.evaluatorDetailInstructions), []);
  const detailModel = useMemo(() => makeDataTourIdResolver(TOUR_IDS.evaluatorDetailModel), []);

  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.evaluateResultDetails, resultDetails);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.evaluatorDetailVersions, detailVersions);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.evaluatorDetailInstructions, detailInstructions);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.evaluatorDetailModel, detailModel);

  // Mirror the `Results` dialog's own `?id` query state so `close()` clears it
  // through the same nuqs writer the dialog reacts to. Held in a ref so the
  // occluder closure stays referentially stable (empty deps) across renders.
  const [, setAnnotationId] = useQueryState("id", parseAsString.withDefault(""));
  const setAnnotationIdRef = useRef(setAnnotationId);
  setAnnotationIdRef.current = setAnnotationId;

  const detailsOccluder = useMemo<OccluderDescriptor>(
    () => ({
      id: TASK_TOUR_OCCLUDERS.evaluateResultsDetails,
      isOpen: isEvaluateResultsDetailsOpen,
      // Returns the nuqs setter promise so reconcile can await the URL clear
      // before its same-route match check.
      close: () => setAnnotationIdRef.current(null, { history: "replace" }),
    }),
    []
  );
  useRegisterOccluder(detailsOccluder);

  return null;
}
