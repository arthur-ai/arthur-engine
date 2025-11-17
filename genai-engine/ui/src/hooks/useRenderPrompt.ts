import { useMutation } from "@tanstack/react-query";

import { useApi } from "./useApi";
import { useTask } from "./useTask";

import type { RenderedPromptResponse, VariableTemplateValue } from "@/lib/api-client/api-client";

interface RenderPromptParams {
  promptName: string;
  promptVersion: string;
  variables: VariableTemplateValue[];
  strict?: boolean;
}

export const useRenderPrompt = () => {
  const { task } = useTask();
  const apiClient = useApi();

  return useMutation<RenderedPromptResponse, Error, RenderPromptParams>({
    mutationFn: async ({ promptName, promptVersion, variables, strict = false }) => {
      if (!task?.id) {
        throw new Error("Task ID not found");
      }

      if (!apiClient) {
        throw new Error("API client not available");
      }

      // Use the API client to call the render endpoint
      // Structure matches the new SavedPromptRenderingRequest with nested completion_request
      const response = await apiClient.api.renderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPost(
        promptName,
        promptVersion,
        task.id,
        {
          completion_request: {
            variables,
            strict,
          },
        }
      );

      return response.data;
    },
  });
};
