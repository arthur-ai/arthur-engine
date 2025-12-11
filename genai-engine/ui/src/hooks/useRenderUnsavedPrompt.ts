import { useQuery } from "@tanstack/react-query";

import { useApi } from "./useApi";

import type { OpenAIMessageInput, VariableTemplateValue } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

interface RenderUnsavedPromptParams {
  messages: OpenAIMessageInput[];
  variables: VariableTemplateValue[];
  strict?: boolean;
  enabled?: boolean;
}

export const useRenderUnsavedPrompt = ({ messages, variables, strict = true, enabled = true }: RenderUnsavedPromptParams) => {
  const apiClient = useApi();

  return useQuery({
    queryKey: [...queryKeys.prompts.renderUnsaved, { messages, variables, strict }],
    queryFn: async () => {
      // Use the API client to call the unsaved render endpoint at /api/v1/prompt_renders
      // Structure matches the new UnsavedPromptRenderingRequest with nested completion_request
      const response = await apiClient?.api.renderUnsavedAgenticPromptApiV1PromptRendersPost({
        messages,
        completion_request: {
          variables,
          strict,
        },
      });

      return response?.data;
    },
    enabled,
  });
};
