import { matchPath } from "react-router-dom";

import { onboardingExerciseTaskId } from "@/lib/tours-config";

import { getTaskIdFromPathname } from "./getTaskIdFromPathname";

const DATASET_DETAIL_PATTERN = "/tasks/:taskId/datasets/:datasetId";
const PROMPT_DETAIL_PATTERN = "/tasks/:taskId/prompts/:promptName";

export function getTourRouteParams(storedParams: Record<string, string>, pathname: string): Record<string, string> {
  const taskIdFromPath = getTaskIdFromPathname(pathname);
  const datasetMatch = matchPath({ path: DATASET_DETAIL_PATTERN, end: false }, pathname);
  const promptMatch = matchPath({ path: PROMPT_DETAIL_PATTERN, end: false }, pathname);

  const taskId = taskIdFromPath ?? storedParams.taskId ?? onboardingExerciseTaskId;

  return {
    ...storedParams,
    taskId,
    ...(datasetMatch?.params.datasetId ? { datasetId: datasetMatch.params.datasetId } : {}),
    ...(promptMatch?.params.promptName ? { promptName: decodeURIComponent(promptMatch.params.promptName) } : {}),
  };
}
