import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

import { PromptType } from "../types";

import { createPrompt, duplicateMessage, duplicatePrompt, newMessage } from "./utils/factories";

import { ModelProvider } from "@/lib/api-client/api-client";

interface PromptPlaygroundActions {
  addPrompt: () => void;
  deletePrompt: (id: string) => void;
  duplicatePrompt: (id: string) => void;

  addMessage: (parentId: string) => void;
  deleteMessage: (parentId: string, id: string) => void;
  duplicateMessage: (parentId: string, id: string) => void;

  setPromptProvider: (id: string, provider: ModelProvider | null) => void;
  setPromptModelName: (id: string, modelName: string | null) => void;
  setPrompt: (id: string, prompt: PromptType) => void;

  hash: () => string;
}

interface PlaygroundStore {
  prompts: PromptType[];
  actions: PromptPlaygroundActions;
}

export const usePromptPlaygroundStore = create<PlaygroundStore>()(
  immer((set, get) => ({
    prompts: [] as PromptType[],
    actions: {
      addPrompt: () => {
        set((state) => {
          state.prompts.push(createPrompt());
        });
      },
      deletePrompt: (id: string) => {
        set((state) => {
          state.prompts = state.prompts.filter((prompt) => prompt.id !== id);
        });
      },
      duplicatePrompt: (id: string) => {
        set((state) => {
          const index = state.prompts.findIndex((prompt) => prompt.id === id);
          const prompt = state.prompts[index];

          if (!prompt) return;

          state.prompts.splice(index + 1, 0, duplicatePrompt(prompt));
        });
      },

      addMessage: (parentId: string) => {
        set((state) => {
          const index = state.prompts.findIndex((prompt) => prompt.id === parentId);
          const prompt = state.prompts[index];

          if (!prompt) return;

          prompt.messages.push(newMessage());
          prompt.isDirty = !!prompt.version;
        });
      },
      deleteMessage: (parentId: string, id: string) => {
        set((state) => {
          const index = state.prompts.findIndex((prompt) => prompt.id === parentId);
          const prompt = state.prompts[index];

          if (!prompt) return;

          prompt.messages = prompt.messages.filter((message) => message.id !== id);
          prompt.isDirty = !!prompt.version;
        });
      },

      duplicateMessage: (parentId: string, id: string) => {
        set((state) => {
          const prompt = state.prompts.find((prompt) => prompt.id === parentId);
          if (!prompt) return;

          const index = prompt.messages.findIndex((message) => message.id === id);
          const message = prompt.messages[index];

          if (!message) return;

          prompt.messages.splice(index + 1, 0, duplicateMessage(message));
          prompt.isDirty = !!prompt.version;
        });
      },

      setPromptProvider: (id: string, provider: ModelProvider | null) => {
        set((state) => {
          const index = state.prompts.findIndex((prompt) => prompt.id === id);
          const prompt = state.prompts[index];

          if (!prompt) return;

          prompt.modelProvider = provider || "";
          prompt.isDirty = !!prompt.version;
        });
      },

      setPromptModelName: (id: string, modelName: string | null) => {
        set((state) => {
          const index = state.prompts.findIndex((prompt) => prompt.id === id);
          const prompt = state.prompts[index];

          if (!prompt) return;

          prompt.modelName = modelName || "";
          prompt.isDirty = !!prompt.version;
        });
      },

      // Overwrite the prompt with the new prompt
      setPrompt: (id: string, prompt: PromptType) => {
        set((state) => {
          const index = state.prompts.findIndex((prompt) => prompt.id === id);

          if (index === -1) return;

          state.prompts[index] = prompt;
        });
      },
      hash: () => {
        const { actions: _, ...state } = get();
        return JSON.stringify(state);
      },
    },
  }))
);
