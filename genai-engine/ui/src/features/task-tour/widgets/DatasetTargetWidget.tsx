import { useMemo } from "react";

import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { TOUR_IDS } from "../selectors";

import { makePreferredDataTourIdResolver } from "./resolvers";

import { useRegisterQueryHook } from "@/features/tour";

/**
 * Registers dataset-specific composite targets. The generate-synthetic and
 * configure-columns steps start on the header trigger, then refresh to the
 * opened modal surface so the spotlight follows the user into the modal (and
 * the modal never reads as occluded / gets auto-closed).
 */
export function DatasetTargetWidget() {
  const generateSynthetic = useMemo(
    () => makePreferredDataTourIdResolver(TOUR_IDS.datasetGenerateSyntheticModal, TOUR_IDS.datasetGenerateSynthetic),
    []
  );
  const configureColumns = useMemo(
    () => makePreferredDataTourIdResolver(TOUR_IDS.datasetConfigureColumnsModal, TOUR_IDS.datasetConfigureColumns),
    []
  );

  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.datasetGenerateSynthetic, generateSynthetic);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.datasetConfigureColumns, configureColumns);

  return null;
}
