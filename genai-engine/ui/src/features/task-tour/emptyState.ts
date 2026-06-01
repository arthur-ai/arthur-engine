import { TASK_TOUR_SKIP_WHEN } from "./content/wiring";

import type { Api } from "@/lib/api";

export type TaskTourEmptyStatePredicate = (skipWhenEmptyKey: string) => boolean | Promise<boolean>;

export function createTaskTourEmptyStatePredicate(api: Api<unknown> | null, taskId: string): TaskTourEmptyStatePredicate {
  return async (skipWhenEmptyKey) => {
    if (skipWhenEmptyKey !== TASK_TOUR_SKIP_WHEN.noEvaluators || !api) {
      return false;
    }

    try {
      const response = await api.api.getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet({
        taskId,
        page: 0,
        page_size: 1,
      });
      return (response.data.count ?? response.data.llm_metadata.length) === 0;
    } catch {
      // Empty-state skipping is a convenience. If the check fails, leave the
      // step in place so the normal missing-target UI can explain the state.
      return false;
    }
  };
}
