import { useCallback, useRef } from "react";

import { PromptAction } from "../types";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

export const useFetchBackendPrompts = () => {
  const isFetchingPrompts = useRef(false);
  const apiClient = useApi();
  const { task } = useTask();
  const taskId = task?.id;

  const fetchPrompts = useCallback(
    async (dispatch: (action: PromptAction) => void) => {
      if (isFetchingPrompts.current) {
        return;
      }

      if (!apiClient || !taskId) {
        console.error("No api client or task id");
        return;
      }

      isFetchingPrompts.current = true;
      try {
        const response = await apiClient.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({
          taskId,
        });

        dispatch({
          type: "updateBackendPrompts",
          payload: { prompts: response.data.prompt_metadata },
        });
      } catch (error) {
        console.error("Failed to fetch prompt metadata:", error);
      } finally {
        isFetchingPrompts.current = false;
      }
    },
    [apiClient, taskId]
  );

  return fetchPrompts;
};
