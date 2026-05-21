import { create } from "zustand";
import { devtools } from "zustand/middleware";

import type { ChatMessage, ChatbotVariant } from "@/hooks/useChatbot";

interface ChatbotState {
  conversations: Record<ChatbotVariant, Record<string, ChatMessage[]>>;
  setMessages: (variant: ChatbotVariant, taskId: string, updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
  reset: (variant: ChatbotVariant, taskId: string) => void;
}

export const useChatbotStore = create<ChatbotState>()(
  devtools(
    (set) => ({
      conversations: { default: {}, demo: {} },
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
      reset: (variant, taskId) =>
        set(
          (state) => {
            const variantConversations = { ...state.conversations[variant] };
            delete variantConversations[taskId];
            return {
              conversations: { ...state.conversations, [variant]: variantConversations },
            };
          },
          false,
          "chatbot/reset"
        ),
    }),
    { name: "chatbot-store" }
  )
);
