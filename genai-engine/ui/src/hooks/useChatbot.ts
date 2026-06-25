import { useCallback, useRef, useState } from "react";

import { useAuth } from "@/contexts/AuthContext";
import { useOutOfCreditsDialog } from "@/contexts/OutOfCreditsContext";
import { API_BASE_URL } from "@/lib/api";
import type { OpenAIMessageInput } from "@/lib/api-client/api-client";
import { getTokenLimitDetail, isTokenLimitExceededError } from "@/lib/api-errors";
import { queryClient } from "@/lib/queryClient";
import { useChatbotStore } from "@/stores/chatbot.store";

export interface ApiToolCallPayload {
  kind: "api";
  method: string;
  path: string;
  status_code?: number;
  body?: unknown;
  tool_call_id?: string;
}

export interface WikiToolCallPayload {
  kind: "wiki";
  name: string;
  query?: string;
  title?: string;
}

export type ToolCallPayload = ApiToolCallPayload | WikiToolCallPayload;

export interface RawToolCall {
  tool_call_id: string;
  name: string;
  arguments: string;
  result?: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "tool_call";
  content: string;
  toolCall?: ToolCallPayload;
  rawToolCall?: RawToolCall;
}

export type ChatbotVariant = "default" | "demo";

interface UseChatbotOptions {
  variant?: ChatbotVariant;
}

interface UseChatbotReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeToolCall: ToolCallPayload | null;
  sendMessage: (message: string) => void;
  clearConversation: () => void;
  abort: () => void;
}

const EMPTY_MESSAGES: ChatMessage[] = [];

function chatMessagesToHistory(messages: ChatMessage[]): OpenAIMessageInput[] {
  const history: OpenAIMessageInput[] = [];
  for (const m of messages) {
    if (m.role === "user") {
      history.push({ role: "user", content: m.content });
    } else if (m.role === "assistant") {
      history.push({ role: "assistant", content: m.content });
    } else if (m.role === "tool_call" && m.rawToolCall) {
      history.push({
        role: "assistant",
        content: null,
        tool_calls: [
          {
            id: m.rawToolCall.tool_call_id,
            type: "function",
            function: {
              name: m.rawToolCall.name,
              arguments: m.rawToolCall.arguments,
            },
          },
        ],
      });
      if (m.rawToolCall.result !== undefined) {
        history.push({
          role: "tool",
          tool_call_id: m.rawToolCall.tool_call_id,
          content: m.rawToolCall.result,
        });
      }
    }
  }
  return history;
}

export function useChatbot(taskId: string, options: UseChatbotOptions = {}): UseChatbotReturn {
  const { variant = "default" } = options;

  const messages = useChatbotStore((s) => s.conversations[variant][taskId] ?? EMPTY_MESSAGES);
  const setStoredMessages = useChatbotStore((s) => s.setMessages);
  const getOrCreateSessionId = useChatbotStore((s) => s.getOrCreateSessionId);
  const resetStored = useChatbotStore((s) => s.reset);

  const [isStreaming, setIsStreaming] = useState(false);
  const [activeToolCall, setActiveToolCall] = useState<ToolCallPayload | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { token } = useAuth();
  const { show: showOutOfCredits } = useOutOfCreditsDialog();

  const updateMessages = useCallback(
    (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
      setStoredMessages(variant, taskId, updater);
    },
    [setStoredMessages, taskId, variant]
  );

  const sendMessage = useCallback(
    (message: string) => {
      if (!token) return;

      const userMessage: ChatMessage = { role: "user", content: message };
      const history: OpenAIMessageInput[] = [...chatMessagesToHistory(messages), { role: "user", content: message }];

      updateMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setActiveToolCall(null);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      const isDemo = variant === "demo";
      let assistantContent = "";
      let lastToolCallPayload: ToolCallPayload | null = null;
      let lastRawToolCall: RawToolCall | null = null;

      const buildToolCallPayload = (raw: Record<string, unknown>): ToolCallPayload => {
        if (isDemo) {
          return {
            kind: "wiki",
            name: String(raw.name ?? ""),
            query: raw.query as string | undefined,
            title: raw.title as string | undefined,
          };
        }
        return {
          kind: "api",
          method: String(raw.method ?? ""),
          path: String(raw.path ?? ""),
          status_code: raw.status_code as number | undefined,
          body: raw.body,
          tool_call_id: raw.tool_call_id as string | undefined,
        };
      };

      const mergeToolResult = (call: ToolCallPayload | null, raw: Record<string, unknown>): ToolCallPayload => {
        if (isDemo) {
          const wikiCall = call?.kind === "wiki" ? call : undefined;
          return {
            kind: "wiki",
            name: String(raw.name ?? wikiCall?.name ?? ""),
            query: (raw.query as string | undefined) ?? wikiCall?.query,
            title: (raw.title as string | undefined) ?? wikiCall?.title,
          };
        }
        const apiCall = call?.kind === "api" ? call : undefined;
        return {
          kind: "api",
          method: String(raw.method ?? apiCall?.method ?? ""),
          path: String(raw.path ?? apiCall?.path ?? ""),
          status_code: raw.status_code as number | undefined,
          body: raw.body,
          tool_call_id: (raw.tool_call_id as string | undefined) ?? apiCall?.tool_call_id,
        };
      };

      const url = isDemo ? `${API_BASE_URL}/api/v1/tasks/${taskId}/demos/chatbot/stream` : `${API_BASE_URL}/api/v1/tasks/${taskId}/chatbot/stream`;

      const body: { history: OpenAIMessageInput[]; session_id?: string } = {
        history,
        session_id: getOrCreateSessionId(variant, taskId),
      };

      (async () => {
        try {
          const response = await fetch(url, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(body),
            signal: abortController.signal,
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            // UP-4390: surface the 429 out-of-credits dialog instead of an
            // inline chat error so the user knows to contact Arthur.
            if (response.status === 429 && isTokenLimitExceededError(errorData)) {
              showOutOfCredits(getTokenLimitDetail(errorData));
              return;
            }
            throw new Error(typeof errorData.detail === "string" ? errorData.detail : `HTTP ${response.status}`);
          }

          if (!response.body) throw new Error("Response body is null");

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          updateMessages((prev) => [...prev, { role: "assistant", content: "" }]);

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
              if (nextLine === undefined) {
                buffer = line + "\n" + buffer;
                break;
              }
              if (!nextLine.startsWith("data: ")) continue;

              const dataStr = nextLine.substring(6).trim();
              i++;

              try {
                console.log("[chatbot]", eventType, dataStr.substring(0, 200));
                if (eventType === "chunk") {
                  const chunk = JSON.parse(dataStr);
                  const content = chunk.choices?.[0]?.delta?.content;
                  if (content) {
                    assistantContent += content;
                    updateMessages((prev) => {
                      const updated = [...prev];
                      updated[updated.length - 1] = { role: "assistant", content: assistantContent };
                      return updated;
                    });
                  }
                } else if (eventType === "search_complete") {
                  assistantContent = "";
                  updateMessages((prev) => [...prev, { role: "assistant", content: "" }]);
                } else if (eventType === "tool_call") {
                  const raw = JSON.parse(dataStr) as Record<string, unknown>;
                  const payload = buildToolCallPayload(raw);
                  lastToolCallPayload = payload;
                  lastRawToolCall = {
                    tool_call_id: String(raw.tool_call_id ?? ""),
                    name: String(raw.name ?? ""),
                    arguments: String(raw.arguments ?? "{}"),
                  };
                  setActiveToolCall(payload);
                } else if (eventType === "tool_result") {
                  const raw = JSON.parse(dataStr) as Record<string, unknown>;
                  const payload = mergeToolResult(lastToolCallPayload, raw);
                  const rawToolCall: RawToolCall | undefined = lastRawToolCall
                    ? { ...lastRawToolCall, result: String(raw.content ?? "") }
                    : undefined;
                  lastToolCallPayload = null;
                  lastRawToolCall = null;
                  setActiveToolCall(null);
                  assistantContent = "";
                  updateMessages((prev) => {
                    // Drop the empty assistant placeholder from the previous iteration if it has no content
                    const last = prev[prev.length - 1];
                    const trimmed = last?.role === "assistant" && !last.content ? prev.slice(0, -1) : prev;
                    return [...trimmed, { role: "tool_call", content: "", toolCall: payload, rawToolCall }, { role: "assistant", content: "" }];
                  });
                } else if (eventType === "final_response") {
                  const finalResponse = JSON.parse(dataStr);
                  updateMessages((prev) => {
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
                } else if (eventType === "history_replace") {
                  const { history: replacement } = JSON.parse(dataStr) as {
                    history: OpenAIMessageInput[];
                  };
                  const replacementMessages: ChatMessage[] = replacement
                    .filter((m) => m.role === "user" || m.role === "assistant")
                    .map((m) => ({
                      role: m.role === "assistant" ? "assistant" : "user",
                      content: typeof m.content === "string" ? m.content : "",
                    }));
                  updateMessages(() => replacementMessages);
                  reader.cancel();
                  break;
                } else if (eventType === "error") {
                  throw new Error(dataStr);
                }
              } catch (parseError) {
                if (parseError instanceof Error && parseError.message === dataStr) {
                  throw parseError;
                }
                console.error("Error parsing SSE event:", parseError, dataStr);
              }
            }
          }
        } catch (error: unknown) {
          if (error instanceof Error && error.name === "AbortError") return;
          const errorMessage = error instanceof Error ? error.message : "Unknown error";
          updateMessages((prev) => {
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
    [getOrCreateSessionId, messages, taskId, token, updateMessages, variant, showOutOfCredits]
  );

  const clearConversation = useCallback(() => {
    setIsStreaming(false);
    setActiveToolCall(null);
    abortControllerRef.current?.abort();
    resetStored(variant, taskId);
  }, [resetStored, taskId, variant]);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  return { messages, isStreaming, activeToolCall, sendMessage, clearConversation, abort };
}
