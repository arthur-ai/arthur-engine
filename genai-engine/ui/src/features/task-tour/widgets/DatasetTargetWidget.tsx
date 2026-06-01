import { useMemo } from "react";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS, type TourId } from "../selectors";

import { useRegisterQueryHook } from "@/features/tour";

function makePreferredDataTourIdResolver(preferredId: TourId, fallbackId: TourId): () => Element | null {
  return () => document.querySelector(tourSelector(preferredId)) ?? document.querySelector(tourSelector(fallbackId));
}

/**
 * Registers dataset-specific composite targets. The generate-synthetic step
 * starts on the header trigger, then refreshes to the modal surface once open.
 */
export function DatasetTargetWidget() {
  const generateSynthetic = useMemo(
    () => makePreferredDataTourIdResolver(TOUR_IDS.datasetGenerateSyntheticModal, TOUR_IDS.datasetGenerateSynthetic),
    []
  );

  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.datasetGenerateSynthetic, generateSynthetic);

  return null;
}
