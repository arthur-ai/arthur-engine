import { useMemo } from "react";
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { ModelParametersType, PromptType } from "../types";

import { useExperimentStore } from "./experiment.store";
import { createPrompt, duplicateMessage, duplicatePrompt, newMessage } from "./utils/factories";

import { MessageRole, ModelProvider } from "@/lib/api-client/api-client";

const now = () => new Date();

interface PromptPlaygroundActions {
  setMode: (mode: "normal" | "config") => void;

  addPrompt: (data?: Partial<PromptType>) => void;
  updatePrompt: (id: string, data: Partial<PromptType>) => void;
  deletePrompt: (id: string) => void;
  duplicatePrompt: (id: string) => void;

  addMessage: (parentId: string) => void;
  deleteMessage: (parentId: string, id: string) => void;
  duplicateMessage: (parentId: string, id: string) => void;

  setPromptProvider: (id: string, provider: ModelProvider | null) => void;
  setPromptModelName: (id: string, modelName: string | null) => void;
  setPrompt: (id: string, prompt: PromptType) => void;

  changeMessageRole: (parentId: string, id: string, role: MessageRole) => void;
  setMessageContent: (parentId: string, id: string, content: string) => void;

  hydrateNotebookState: (prompts: PromptType[], keywords: Map<string, string>) => void;
  overwritePrompts: (prompts: PromptType[]) => void;

  updateKeywords: (id: string, messageKeywords: string[]) => void;
  updateKeywordValue: (keyword: string, value: string) => void;

  updateModelParameters: (promptId: string, modelParameters: ModelParametersType) => void;
  updateResponseFormat: (promptId: string, responseFormat: string | undefined) => void;

  runPrompt: (promptId: string) => void;

  resetMutation: () => void;

  reset: () => void;
}

interface PlaygroundStore {
  mode: "normal" | "config";
  prompts: PromptType[];
  keywords: Map<string, string>;
  keywordTracker: Map<string, Array<string>>;
  mutation: {
    savedAt: Date | null;
    changedAt: Date | null;
  };

  actions: PromptPlaygroundActions;
}

export const usePromptPlaygroundStore = create<PlaygroundStore>()(
  devtools(
    immer((set, get) => ({
      mode: "normal",
      prompts: [] as PromptType[],
      keywords: new Map<string, string>(),
      keywordTracker: new Map<string, Array<string>>(),
      mutation: {
        savedAt: null,
        changedAt: null,
      },
      actions: {
        setMode: (mode: "normal" | "config") => {
          set({ mode }, false, "playground/setMode");
        },

        addPrompt: (data?: Partial<PromptType>) => {
          set(
            (state) => {
              state.prompts.push(createPrompt(data));
              state.mutation.changedAt = now();
            },
            false,
            "playground/addPrompt"
          );
        },
        updatePrompt: (id: string, data: Partial<PromptType>) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === id);
              const prompt = state.prompts[index];
              if (!prompt) return;

              state.prompts[index] = { ...prompt, ...data };
              state.prompts[index].isDirty = !!prompt.version;
              state.mutation.changedAt = now();
            },
            false,
            "playground/updatePrompt"
          );
        },
        deletePrompt: (id: string) => {
          set(
            (state) => {
              state.prompts = state.prompts.filter((prompt) => prompt.id !== id);
              state.mutation.changedAt = now();
            },
            false,
            "playground/deletePrompt"
          );
        },
        duplicatePrompt: (id: string) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === id);
              const prompt = state.prompts[index];

              if (!prompt) return;

              state.prompts.splice(index + 1, 0, duplicatePrompt(prompt));
              state.mutation.changedAt = now();
            },
            false,
            "playground/duplicatePrompt"
          );
        },

        addMessage: (parentId: string) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === parentId);
              const prompt = state.prompts[index];

              if (!prompt) return;

              prompt.messages.push(newMessage());
              prompt.isDirty = !!prompt.version;
              state.mutation.changedAt = now();
            },
            false,
            "playground/addMessage"
          );
        },
        deleteMessage: (parentId: string, id: string) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === parentId);
              const prompt = state.prompts[index];

              if (!prompt) return;

              prompt.messages = prompt.messages.filter((message) => message.id !== id);
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/deleteMessage"
          );
        },

        duplicateMessage: (parentId: string, id: string) => {
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === parentId);
              if (!prompt) return;

              const index = prompt.messages.findIndex((message) => message.id === id);
              const message = prompt.messages[index];

              if (!message) return;

              prompt.messages.splice(index + 1, 0, duplicateMessage(message));
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/duplicateMessage"
          );
        },

        setPromptProvider: (id: string, provider: ModelProvider | null) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === id);
              const prompt = state.prompts[index];

              if (!prompt) return;

              prompt.modelProvider = provider || "";
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/setPromptProvider"
          );
        },

        setPromptModelName: (id: string, modelName: string | null) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === id);
              const prompt = state.prompts[index];

              if (!prompt) return;

              prompt.modelName = modelName || "";
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/setPromptModelName"
          );
        },

        // Overwrite the prompt with the new prompt
        setPrompt: (id: string, prompt: PromptType) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === id);

              if (index === -1) return;

              state.prompts[index] = prompt;
              state.mutation.changedAt = now();
            },
            false,
            "playground/setPrompt"
          );
        },

        changeMessageRole: (parentId: string, id: string, role: MessageRole) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === parentId);
              const prompt = state.prompts[index];
              if (!prompt) return;

              prompt.messages = prompt.messages.map((message) => (message.id === id ? { ...message, role } : message));
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/changeMessageRole"
          );
        },
        setMessageContent: (parentId: string, id: string, content: string) => {
          set(
            (state) => {
              const index = state.prompts.findIndex((prompt) => prompt.id === parentId);
              const prompt = state.prompts[index];
              if (!prompt) return;

              prompt.messages = prompt.messages.map((message) => (message.id === id ? { ...message, content } : message));
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/setMessageContent"
          );
        },

        hydrateNotebookState: (prompts: PromptType[], keywords: Map<string, string>) => {
          set(
            (state) => {
              state.prompts = prompts;
              state.keywords = new Map(keywords);
              state.mutation.savedAt = now();
              state.mutation.changedAt = null;
            },
            false,
            "playground/hydrateNotebookState"
          );
        },
        overwritePrompts: (prompts: PromptType[]) => {
          set(
            (state) => {
              state.prompts = prompts;
              state.mutation.changedAt = now();
            },
            false,
            "playground/overwritePrompts"
          );
        },

        updateKeywords: (id: string, messageKeywords: string[], dirty = false) => {
          set(
            (state) => {
              const newKeywordTracker = new Map<string, Array<string>>(get().keywordTracker);

              if (messageKeywords.length === 0) {
                newKeywordTracker.delete(id);
              } else {
                newKeywordTracker.set(id, messageKeywords);
              }

              const inUseKeywords = new Set<string>();
              newKeywordTracker.forEach((keywords) => {
                keywords.forEach((keyword) => inUseKeywords.add(keyword));
              });

              const newKeywords = new Map<string, string>(get().keywords);
              inUseKeywords.forEach((keyword) => {
                if (!newKeywords.has(keyword)) {
                  newKeywords.set(keyword, "");
                }
              });

              for (const keyword of newKeywords.keys()) {
                if (!inUseKeywords.has(keyword)) {
                  newKeywords.delete(keyword);
                }
              }

              state.keywords = newKeywords;
              state.keywordTracker = newKeywordTracker;
              if (dirty) {
                state.mutation.changedAt = now();
              }
            },
            false,
            "playground/updateKeywords"
          );
        },

        updateKeywordValue: (keyword: string, value: string) => {
          set(
            (state) => {
              const newKeywords = new Map<string, string>(get().keywords);
              newKeywords.set(keyword, value);
              state.keywords = newKeywords;
              state.mutation.changedAt = now();
            },
            false,
            "playground/updateKeywordValue"
          );
        },

        updateModelParameters: (promptId: string, modelParameters: ModelParametersType) => {
          set(
            (state) => {
              state.prompts = state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, modelParameters } : prompt));
              state.mutation.changedAt = now();
            },
            false,
            "playground/updateModelParameters"
          );
        },

        updateResponseFormat: (promptId: string, responseFormat: string | undefined) => {
          set(
            (state) => {
              state.prompts = state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, responseFormat } : prompt));
              state.mutation.changedAt = now();
            },
            false,
            "playground/updateResponseFormat"
          );
        },

        runPrompt: (promptId: string) => {
          set(
            (state) => {
              state.prompts = state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, running: true } : prompt));
              state.mutation.changedAt = now();
            },
            false,
            "playground/runPrompt"
          );
        },

        resetMutation: () => {
          set(
            (state) => {
              state.mutation.savedAt = now();
              state.mutation.changedAt = now();
            },
            false,
            "playground/resetMutation"
          );
        },

        reset: () => {
          set(
            {
              prompts: [],
              keywords: new Map<string, string>(),
              keywordTracker: new Map<string, Array<string>>(),
              mutation: { savedAt: null, changedAt: null },
            },
            false,
            "playground/reset"
          );
        },
      },
    }))
  )
);

export const useIsPlaygroundDirty = () => {
  return usePromptPlaygroundStore(({ mutation }) => !!mutation.changedAt && (!mutation.savedAt || mutation.changedAt > mutation.savedAt));
};

export const useBlankVariableCount = () => {
  const mode = usePromptPlaygroundStore(({ mode }) => mode);
  const keywords = usePromptPlaygroundStore(({ keywords }) => keywords);
  const experimentConfig = useExperimentStore(({ experimentConfig }) => experimentConfig);

  return useMemo(() => {
    if (mode === "config") {
      const mapped = new Set([...(experimentConfig?.prompt_variable_mapping?.map((mapping) => mapping.variable_name) || [])]);

      return Array.from(keywords).filter(([key, value]) => !mapped.has(key) && (!value || value.trim() === "")).length;
    }

    return Array.from(keywords.values()).filter((value) => !value || value.trim() === "").length;
  }, [mode, keywords, experimentConfig]);
};

export const useAllPromptsHaveModelConfig = () => {
  const prompts = usePromptPlaygroundStore(({ prompts }) => prompts);

  return useMemo(() => {
    return prompts.every((prompt) => prompt.modelProvider !== "" && prompt.modelName !== "");
  }, [prompts]);
};
