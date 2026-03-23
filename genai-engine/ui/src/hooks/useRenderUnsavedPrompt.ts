import { useMutation } from "@tanstack/react-query";

import { useApi } from "./useApi";

import type { OpenAIMessageInput, RenderedPromptResponse, VariableTemplateValue } from "@/lib/api-client/api-client";

interface RenderUnsavedPromptParams {
  messages: OpenAIMessageInput[];
  variables: VariableTemplateValue[];
  strict?: boolean;
}

export const useRenderUnsavedPrompt = () => {
  const apiClient = useApi();

  return useMutation<RenderedPromptResponse, Error, RenderUnsavedPromptParams>({
    mutationFn: async ({ messages, variables, strict = true }) => {
      if (!apiClient) {
        throw new Error("API client not available");
      }

      // Use the API client to call the unsaved render endpoint at /api/v1/prompt_renders
      // Structure matches the new UnsavedPromptRenderingRequest with nested completion_request
      const response = await apiClient.api.renderUnsavedAgenticPromptApiV1PromptRendersPost({
        messages,
        completion_request: {
          variables,
          strict,
        },
      });

      return response.data;
    },
  });
};
