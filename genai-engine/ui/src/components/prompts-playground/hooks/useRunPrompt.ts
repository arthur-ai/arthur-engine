import { AxiosError } from "axios";
import { useCallback, useRef, useEffect } from "react";

import { useApi } from "../../../hooks/useApi";

import { usePromptContext } from "@/components/prompts-playground/PromptsPlaygroundContext";
import { PromptType } from "@/components/prompts-playground/types";
import { streamCompletions } from "@/components/prompts-playground/utils/streamCompletions";
import toCompletionRequest from "@/components/prompts-playground/utils/toCompletionRequest";
import { useAuth } from "@/contexts/AuthContext";
import { AgenticPromptRunResponse, RunAgenticPromptApiV1CompletionsPostError } from "@/lib/api-client/api-client";

interface UseRunPromptOptions {
  prompt: PromptType;
  onError?: (error: string) => void;
}

/**
 * Hook to run a prompt with support for both streaming and non-streaming requests
 * @param options Configuration options including the prompt to run
 * @returns A function to run the prompt
 */
const useRunPrompt = ({ prompt, onError }: UseRunPromptOptions) => {
  const { state, dispatch } = usePromptContext();
  const apiClient = useApi();
  const { token } = useAuth();
  const abortControllerRef = useRef<AbortController | null>(null);
  const isRunningRef = useRef<boolean>(false);

  // Cleanup on unmount or when prompt changes
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      isRunningRef.current = false;
    };
  }, [prompt.id]);

  const runPrompt = useCallback(async () => {
    if (!apiClient) {
      console.error("No API client available");
      onError?.("No API client available. Please check the console for more details.");
      return;
    }

    // Prevent running if already running (prevents infinite loops and duplicate requests)
    if (isRunningRef.current) {
      return;
    }

    // Replace template strings with variable values before sending to API
    const completionRequest = toCompletionRequest(prompt, state.keywords);

    const isStreaming = completionRequest.completion_request?.stream ?? false;
    if (isStreaming) {
      // Cancel any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Mark as running
      isRunningRef.current = true;

      // Start streaming (pass token as fallback for auth headers)
      abortControllerRef.current = streamCompletions(
        completionRequest,
        apiClient,
        {
          onChunk: (content: string) => {
            // Update content incrementally
            dispatch({
              type: "updatePrompt",
              payload: {
                promptId: prompt.id,
                prompt: {
                  running: true,
                  runResponse: {
                    content,
                    cost: "0.000000", // Cost will be updated in final_response
                    tool_calls: null,
                  },
                },
              },
            });
          },
          onFinalResponse: (response: AgenticPromptRunResponse) => {
            // Update with final response including cost and tool_calls
            isRunningRef.current = false;
            dispatch({
              type: "updatePrompt",
              payload: {
                promptId: prompt.id,
                prompt: {
                  running: false,
                  runResponse: response,
                },
              },
            });
            abortControllerRef.current = null;
          },
          onError: (error: string) => {
            console.error("Error streaming prompt:", error);
            isRunningRef.current = false;
            onError?.(`${error}. Please check the console for more details.`);
            dispatch({
              type: "updatePrompt",
              payload: {
                promptId: prompt.id,
                prompt: {
                  running: false,
                  runResponse: null,
                },
              },
            });
            abortControllerRef.current = null;
          },
        },
        token || undefined
      );
    } else {
      // Non-streaming path
      isRunningRef.current = true;
      try {
        const response = await apiClient.api.runAgenticPromptApiV1CompletionsPost(completionRequest);
        isRunningRef.current = false;
        dispatch({
          type: "updatePrompt",
          payload: {
            promptId: prompt.id,
            prompt: {
              running: false,
              runResponse: response.data,
            },
          },
        });
      } catch (error: unknown) {
        isRunningRef.current = false;
        console.error("Error running prompt:", error);
        let errorMessage = "Error running prompt";

        // Axios throws AxiosError, with the typed error response in error.response.data
        if (error instanceof AxiosError) {
          const errorData = error.response?.data as RunAgenticPromptApiV1CompletionsPostError | undefined;
          if (errorData?.detail) {
            // HTTPValidationError has detail as ValidationError[] or sometimes string
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail.map((err: { msg?: string }) => err.msg || JSON.stringify(err)).join(", ");
            } else if (typeof errorData.detail === "string") {
              errorMessage = errorData.detail;
            }
          } else if (error.message) {
            errorMessage = error.message;
          }
        } else if (error instanceof Error) {
          errorMessage = error.message;
        }

        onError?.(`${errorMessage}. Please check the console for more details.`);
        dispatch({
          type: "updatePrompt",
          payload: {
            promptId: prompt.id,
            prompt: {
              running: false,
              runResponse: null,
            },
          },
        });
      }
    }
  }, [apiClient, prompt, state.keywords, dispatch, onError, token]);

  return runPrompt;
};

export default useRunPrompt;
