import { debounce } from "@mui/material/utils";
import { useCallback, useRef, useMemo } from "react";

import { MessageType } from "../types";
import { convertMessagesToApiFormat } from "../utils/messageUtils";

import { useApi } from "@/hooks/useApi";

const DEBOUNCE_TIME = 500;

/**
 * Hook that extracts variables from prompt messages using the backend API.
 * Debounces API calls to avoid excessive requests.
 *
 * @returns Object with extractVariables and debouncedExtractVariables functions
 */
export const useExtractPromptVariables = () => {
  const apiClient = useApi();
  const abortControllerRef = useRef<AbortController | null>(null);

  const extractVariables = useCallback(
    async (messages: MessageType[]): Promise<string[]> => {
      if (!apiClient || messages.length === 0) {
        return [];
      }

      // Cancel any pending request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();

      try {
        // Convert messages to API format
        const apiMessages = convertMessagesToApiFormat(messages);

        // Call the backend API
        const response = await apiClient.api.getUnsavedPromptVariablesListApiV1PromptVariablesPost(
          { messages: apiMessages },
          { signal: abortControllerRef.current.signal }
        );

        return response.data.variables || [];
      } catch (error: unknown) {
        // Handle errors gracefully - return empty array
        // Don't log aborted requests (they're expected when debouncing)
        if (error instanceof Error && error.name !== "AbortError") {
          console.error("Failed to extract prompt variables:", error);
        }
        return [];
      }
    },
    [apiClient]
  );

  // Debounce the extraction function with callback
  // Use useMemo to recreate when extractVariables changes
  const debouncedExtractVariables = useMemo(
    () =>
      debounce((messages: MessageType[], callback: (variables: string[]) => void) => {
        extractVariables(messages).then(callback);
      }, DEBOUNCE_TIME),
    [extractVariables]
  );

  return {
    extractVariables,
    debouncedExtractVariables,
  };
};
