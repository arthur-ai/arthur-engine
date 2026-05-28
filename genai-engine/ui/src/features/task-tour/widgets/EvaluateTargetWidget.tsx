import { useMemo } from "react";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS, type TourId } from "../selectors";

import { useRegisterQueryHook } from "@/features/tour";

function makePreferredDataTourIdResolver(preferredId: TourId, fallbackId: TourId): () => Element | null {
  return () => document.querySelector(tourSelector(preferredId)) ?? document.querySelector(tourSelector(fallbackId));
}

/**
 * Registers Evaluate-page composite targets. Results detail starts on the
 * first results row, then retargets to the details dialog once it opens.
 */
export function EvaluateTargetWidget() {
  const resultDetails = useMemo(() => makePreferredDataTourIdResolver(TOUR_IDS.evaluateResultsDetailsDialog, TOUR_IDS.evaluateResultsFirstRow), []);

  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.evaluateResultDetails, resultDetails);

  return null;
}
