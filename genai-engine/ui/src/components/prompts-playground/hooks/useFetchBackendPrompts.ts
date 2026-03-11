import { useCallback, useRef } from "react";

import { PromptAction } from "../types";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";

const PAGE_SIZE = 100;

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
        // Fetch first page to get total count, then fetch remaining pages
        const firstResponse = await apiClient.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({
          taskId,
          page_size: PAGE_SIZE,
          page: 0,
        });

        const allPrompts: LLMGetAllMetadataResponse[] = [...firstResponse.data.llm_metadata];
        const totalCount = firstResponse.data.count;

        let page = 1;
        while (allPrompts.length < totalCount) {
          const response = await apiClient.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({
            taskId,
            page_size: PAGE_SIZE,
            page,
          });
          if (response.data.llm_metadata.length === 0) break;
          allPrompts.push(...response.data.llm_metadata);
          page += 1;
        }

        dispatch({
          type: "updateBackendPrompts",
          payload: { prompts: allPrompts },
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
