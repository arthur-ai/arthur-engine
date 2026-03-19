import { useCallback, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";

import { useAuth } from "@/contexts/AuthContext";
import { useApi } from "@/hooks/useApi";
import { API_BASE_URL } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";

export interface ChatMessage {
  role: "user" | "assistant" | "tool_call";
  content: string;
  method?: string;
  path?: string;
  status_code?: number;
}

export interface ToolCallEvent {
  method: string;
  path: string;
}

interface UseChatbotReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeToolCall: ToolCallEvent | null;
  conversationId: string;
  sendMessage: (message: string) => void;
  clearConversation: () => void;
  abort: () => void;
}

export function useChatbot(taskId: string): UseChatbotReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeToolCall, setActiveToolCall] = useState<ToolCallEvent | null>(null);
  const [conversationId] = useState(() => uuidv4());
  const abortControllerRef = useRef<AbortController | null>(null);
  const { token } = useAuth();
  const api = useApi();

  const sendMessage = useCallback(
    (message: string) => {
      if (!token) return;

      const userMessage: ChatMessage = { role: "user", content: message };

      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setActiveToolCall(null);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let assistantContent = "";

      (async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/chatbot/stream`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              message,
              conversation_id: conversationId,
            }),
            signal: abortController.signal,
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
          }

          if (!response.body) throw new Error("Response body is null");

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (let i = 0; i < lines.length; i++) {
              const line = lines[i];
              if (!line.startsWith("event: ")) continue;

              const eventType = line.substring(7).trim();
              const nextLine = lines[i + 1];
              if (!nextLine?.startsWith("data: ")) continue;

              const dataStr = nextLine.substring(6).trim();
              i++;

              try {
                console.log("[chatbot]", eventType, dataStr.substring(0, 200));
                if (eventType === "chunk") {
                  const chunk = JSON.parse(dataStr);
                  const content = chunk.choices?.[0]?.delta?.content;
                  if (content) {
                    assistantContent += content;
                    setMessages((prev) => {
                      const updated = [...prev];
                      updated[updated.length - 1] = { role: "assistant", content: assistantContent };
                      return updated;
                    });
                  }
                } else if (eventType === "search_complete") {
                  assistantContent = "";
                  setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
                } else if (eventType === "tool_call") {
                  const toolCallData = JSON.parse(dataStr);
                  setActiveToolCall(toolCallData);
                } else if (eventType === "tool_result") {
                  const toolResult = JSON.parse(dataStr);
                  setActiveToolCall(null);
                  assistantContent = "";
                  setMessages((prev) => {
                    // Drop the empty assistant placeholder from the previous iteration if it has no content
                    const last = prev[prev.length - 1];
                    const trimmed = last?.role === "assistant" && !last.content ? prev.slice(0, -1) : prev;
                    return [
                      ...trimmed,
                      {
                        role: "tool_call",
                        content: "",
                        method: toolResult.method,
                        path: toolResult.path,
                        status_code: toolResult.status_code,
                        body: toolResult.body,
                        tool_call_id: toolResult.tool_call_id,
                      },
                      { role: "assistant", content: "" },
                    ];
                  });
                } else if (eventType === "final_response") {
                  const finalResponse = JSON.parse(dataStr);
                  setMessages((prev) => {
                    const updated = [...prev];
                    if (finalResponse.content) {
                      updated[updated.length - 1] = {
                        role: "assistant",
                        content: finalResponse.content,
                      };
                    } else {
                      // No text response — remove the empty placeholder
                      updated.pop();
                    }
                    return updated;
                  });
                  reader.cancel();
                  break;
                } else if (eventType === "error") {
                  throw new Error(dataStr);
                }
              } catch (parseError) {
                console.error("Error parsing SSE event:", parseError, dataStr);
              }
            }
          }
        } catch (error: unknown) {
          if (error instanceof Error && error.name === "AbortError") return;
          const errorMessage = error instanceof Error ? error.message : "Unknown error";
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", content: `Error: ${errorMessage}` };
            return updated;
          });
        } finally {
          setIsStreaming(false);
          setActiveToolCall(null);
          queryClient.invalidateQueries();
        }
      })();
    },
    [conversationId, token, taskId]
  );

  const clearConversation = useCallback(() => {
    setMessages([]);
    setIsStreaming(false);
    setActiveToolCall(null);
    api?.api.clearChatbotHistoryApiV1ChatbotHistoryConversationIdDelete(conversationId).catch(() => {});
  }, [api, conversationId]);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  return { messages, isStreaming, activeToolCall, conversationId, sendMessage, clearConversation, abort };
}
