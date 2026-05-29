import { useMemo } from "react";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS, type TourId } from "../selectors";

import { useRegisterQueryHook } from "@/features/tour";

function makePreferredDataTourIdResolver(preferredId: TourId, fallbackId: TourId): () => Element | null {
  return () => document.querySelector(tourSelector(preferredId)) ?? document.querySelector(tourSelector(fallbackId));
}

function makeDataTourIdResolver(id: TourId): () => Element | null {
  return () => document.querySelector(tourSelector(id));
}

/**
 * Registers Evaluate-page composite targets. Results detail starts on the
 * first results row, then retargets to the details dialog once it opens.
 *
 * The evaluator-detail hooks back the "Review an evaluator" mini-tour: after
 * the user maximizes an evaluator, these resolvers poll for the version
 * drawer, instructions panel, and judge-model field on the full-screen detail
 * view (which mount asynchronously once the eval data loads).
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

  return null;
}
