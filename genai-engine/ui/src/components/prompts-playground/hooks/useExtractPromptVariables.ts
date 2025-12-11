import { useQuery, UseQueryResult } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { MessageType } from "../types";
import { convertMessagesToApiFormat, hasTemplateVariables } from "../utils/messageUtils";

import { useApi } from "@/hooks/useApi";

const DEBOUNCE_TIME = 500;

/**
 * Hook that extracts variables from prompt messages using the backend API.
 * Debounces API calls to avoid excessive requests.
 * Uses React Query for caching, request cancellation, and error handling.
 * Optimizes by skipping API calls when no template patterns are detected.
 *
 * @param messages - Array of messages to extract variables from
 * @returns React Query result object with variables data
 */
export const useExtractPromptVariables = (messages: MessageType[]): UseQueryResult<string[], Error> => {
  const apiClient = useApi();
  const [debouncedMessages, setDebouncedMessages] = useState<MessageType[]>(messages);

  // Debounce messages to avoid excessive API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedMessages(messages);
    }, DEBOUNCE_TIME);

    return () => clearTimeout(timer);
  }, [messages]);

  return useQuery<string[], Error>({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: ["extractPromptVariables", debouncedMessages],
    queryFn: async () => {
      if (!apiClient || debouncedMessages.length === 0) {
        return [];
      }

      try {
        // Convert messages to API format
        const apiMessages = convertMessagesToApiFormat(debouncedMessages);

        // Call the backend API
        const response = await apiClient.api.getUnsavedPromptVariablesListApiV1PromptVariablesPost({
          messages: apiMessages,
        });

        return response.data.variables || [];
      } catch (error: unknown) {
        // Handle errors gracefully - return empty array
        if (error instanceof Error) {
          console.error("Failed to extract prompt variables:", error);
        }
        return [];
      }
    },
    enabled: !!apiClient && debouncedMessages.length > 0 && hasTemplateVariables(debouncedMessages),
    retry: false,
    // Default to empty array
    placeholderData: [],
  });
};
