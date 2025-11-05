import { Api } from "@/lib/api-client/api-client";
import { CompletionRequest, AgenticPromptRunResponse } from "@/lib/api-client/api-client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000");

interface StreamChunk {
  id?: string;
  created?: number;
  model?: string;
  object?: string;
  system_fingerprint?: string;
  choices?: Array<{
    finish_reason?: string | null;
    index?: number;
    delta?: {
      provider_specific_fields?: unknown;
      refusal?: string | null;
      content?: string;
      role?: string | null;
      function_call?: unknown;
      tool_calls?: unknown;
      audio?: unknown;
    };
    logprobs?: unknown;
  }>;
  provider_specific_fields?: unknown;
}

interface StreamCallbacks {
  onChunk: (content: string) => void;
  onFinalResponse: (response: AgenticPromptRunResponse) => void;
  onError: (error: string) => void;
}

/**
 * Streams a completion request using Server-Sent Events (SSE)
 * @param completionRequest The completion request to stream
 * @param apiClient The API client instance (used to extract baseURL and auth headers)
 * @param callbacks Callbacks for handling stream events
 * @param token Optional authentication token (fallback if not found in apiClient headers)
 * @returns AbortController for canceling the stream
 */
export function streamCompletions(
  completionRequest: CompletionRequest,
  apiClient: Api<unknown>,
  callbacks: StreamCallbacks,
  token?: string
): AbortController {
  const abortController = new AbortController();
  let accumulatedContent = "";

  // Extract baseURL from API client instance
  const baseURL = apiClient.instance.defaults.baseURL || API_BASE_URL;

  // Extract auth headers from API client instance
  const getAuthHeaders = async (): Promise<Record<string, string>> => {
    // Try to get headers from instance defaults (common headers are set for all methods)
    const commonHeaders = apiClient.instance.defaults.headers?.common as Record<string, string> | undefined;
    const authHeader = commonHeaders?.Authorization;

    if (authHeader) {
      return { Authorization: authHeader };
    }

    // Fallback: try to get from POST-specific headers
    const postHeaders = apiClient.instance.defaults.headers?.post as Record<string, string> | undefined;
    if (postHeaders?.Authorization) {
      return { Authorization: postHeaders.Authorization };
    }

    // Additional fallback: check if axios interceptors set headers
    // We can't access private securityWorker, but we can check if headers were set via interceptors
    const allHeaders = apiClient.instance.defaults.headers as Record<string, unknown> | undefined;
    if (allHeaders && typeof allHeaders === "object" && "Authorization" in allHeaders) {
      const authHeader = allHeaders.Authorization;
      if (typeof authHeader === "string") {
        return { Authorization: authHeader };
      }
    }

    // Final fallback: use provided token if available
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }

    // If no auth header found, the request will fail but that's expected
    // The user should see an authentication error
    return {};
  };

  // Start streaming
  (async () => {
    try {
      const authHeaders = await getAuthHeaders();

      const response = await fetch(`${baseURL}/api/v1/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify(completionRequest),
        signal: abortController.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events (lines ending with \n\n)
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];

          // SSE format: "event: <eventType>" followed by "data: <json>"
          if (line.startsWith("event: ")) {
            const eventType = line.substring(7).trim();
            const nextLine = lines[i + 1];

            if (nextLine && nextLine.startsWith("data: ")) {
              const dataStr = nextLine.substring(6).trim();

              if (dataStr) {
                try {
                  if (eventType === "chunk") {
                    const chunk: StreamChunk = JSON.parse(dataStr);
                    // Extract content from the chunk
                    const content = chunk.choices?.[0]?.delta?.content;
                    if (content) {
                      accumulatedContent += content;
                      callbacks.onChunk(accumulatedContent);
                    }
                  } else if (eventType === "final_response") {
                    const finalResponse: AgenticPromptRunResponse = JSON.parse(dataStr);
                    callbacks.onFinalResponse(finalResponse);
                    // Stop reading after final response
                    reader.cancel();
                    return;
                  } else if (eventType === "error") {
                    const errorMessage = JSON.parse(dataStr);
                    callbacks.onError(typeof errorMessage === "string" ? errorMessage : errorMessage.detail || "Unknown error");
                    reader.cancel();
                    return;
                  }
                } catch (parseError) {
                  console.error("Error parsing SSE data:", parseError, dataStr);
                }
              }
            }
            i++; // Skip the data line since we processed it
          }
        }
      }
    } catch (error: unknown) {
      if (error instanceof Error && error.name === "AbortError") {
        // User canceled the stream - this is expected
        return;
      }
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      callbacks.onError(errorMessage);
    }
  })();

  return abortController;
}
