import { create } from "zustand";
import { devtools } from "zustand/middleware";

import type { ChatMessage, ChatbotVariant } from "@/hooks/useChatbot";

interface ChatbotState {
  conversations: Record<ChatbotVariant, Record<string, ChatMessage[]>>;
  sessionIds: Record<ChatbotVariant, Record<string, string>>;
  setMessages: (variant: ChatbotVariant, taskId: string, updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
  getOrCreateSessionId: (variant: ChatbotVariant, taskId: string) => string;
  reset: (variant: ChatbotVariant, taskId: string) => void;
}

export const useChatbotStore = create<ChatbotState>()(
  devtools(
    (set, get) => ({
      conversations: { default: {}, demo: {} },
      sessionIds: { default: {}, demo: {} },
      setMessages: (variant, taskId, updater) =>
        set(
          (state) => {
            const variantConversations = state.conversations[variant];
            const prev = variantConversations[taskId] ?? [];
            return {
              conversations: {
                ...state.conversations,
                [variant]: { ...variantConversations, [taskId]: updater(prev) },
              },
            };
          },
          false,
          "chatbot/setMessages"
        ),
      getOrCreateSessionId: (variant, taskId) => {
        const existing = get().sessionIds[variant][taskId];
        if (existing) return existing;
        const newId = variant === "demo" ? `demo-session-${crypto.randomUUID()}` : crypto.randomUUID();
        set(
          (state) => ({
            sessionIds: {
              ...state.sessionIds,
              [variant]: { ...state.sessionIds[variant], [taskId]: newId },
            },
          }),
          false,
          "chatbot/createSessionId"
        );
        return newId;
      },
      reset: (variant, taskId) =>
        set(
          (state) => {
            const variantConversations = { ...state.conversations[variant] };
            delete variantConversations[taskId];
            const variantSessionIds = { ...state.sessionIds[variant] };
            delete variantSessionIds[taskId];
            return {
              conversations: { ...state.conversations, [variant]: variantConversations },
              sessionIds: { ...state.sessionIds, [variant]: variantSessionIds },
            };
          },
          false,
          "chatbot/reset"
        ),
    }),
    { name: "chatbot-store" }
  )
);
