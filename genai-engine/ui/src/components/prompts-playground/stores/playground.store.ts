import { useMemo } from "react";
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { FrontendTool, ModelParametersType, PromptType } from "../types";
import { arrayUtils, cleanupAndRecalculateKeywords } from "../utils";

import { useExperimentStore } from "./experiment.store";
import { createPrompt, createTool, duplicateMessage, duplicatePrompt, newMessage } from "./utils/factories";

import { MessageRole, ModelProvider, ToolCall, ToolChoice, ToolChoiceEnum } from "@/lib/api-client/api-client";

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
  moveMessage: (parentId: string, oldIndex: number, newIndex: number) => void;

  setPromptProvider: (id: string, provider: ModelProvider | null) => void;
  setPromptModelName: (id: string, modelName: string | null) => void;
  setPrompt: (id: string, prompt: PromptType) => void;

  changeMessageRole: (parentId: string, id: string, role: MessageRole) => void;
  setMessageContent: (parentId: string, id: string, content: string) => void;
  editMessageToolCalls: (parentId: string, id: string, toolCalls: ToolCall[] | null) => void;
  addTool: (promptId: string) => void;
  deleteTool: (promptId: string, toolId: string) => void;
  updateToolChoice: (promptId: string, toolChoice: ToolChoiceEnum | ToolChoice) => void;
  updateTool: (promptId: string, toolId: string, tool: Partial<FrontendTool>) => void;

  hydrateNotebookState: (prompts: PromptType[], keywords: Map<string, string>) => void;
  overwritePrompts: (prompts: PromptType[]) => void;

  updateKeywords: (id: string, messageKeywords: string[]) => void;
  updateKeywordValue: (keyword: string, value: string) => void;
  extractPromptVariables: (promptId: string, variables: string[]) => void;

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
              state.prompts[index].isDirty =
                data.isDirty !== undefined ? data.isDirty : data.version !== undefined && data.messages !== undefined ? false : prompt.isDirty;
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

        moveMessage: (parentId: string, oldIndex: number, newIndex: number) => {
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === parentId);
              if (!prompt) return;

              prompt.messages = arrayUtils.moveItem(prompt.messages, oldIndex, newIndex);
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/moveMessage"
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

        editMessageToolCalls: (parentId: string, id: string, toolCalls: ToolCall[] | null) => {
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === parentId);
              if (!prompt) return;

              const index = prompt.messages.findIndex((message) => message.id === id);
              const message = prompt.messages[index];
              if (!message) return;

              const oldToolCalls = message.tool_calls ?? null;
              const newToolCalls = toolCalls ?? null;
              const wasChanged = JSON.stringify(oldToolCalls) !== JSON.stringify(newToolCalls);

              if (wasChanged && prompt.version) {
                prompt.isDirty = true;
                state.mutation.changedAt = now();
              }
            },
            false,
            "playground/editMessageToolCalls"
          );
        },

        addTool: (promptId: string) => {
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === promptId);
              if (!prompt) return;

              prompt.tools.push(createTool(prompt.tools.length + 1));
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/addTool"
          );
        },

        deleteTool: (promptId: string, toolId: string) => {
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === promptId);
              if (!prompt) return;

              prompt.tools = prompt.tools.filter((tool) => tool.id !== toolId);
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/deleteTool"
          );
        },

        updateToolChoice: (promptId: string, toolChoice: ToolChoiceEnum | ToolChoice) => {
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === promptId);
              if (!prompt) return;

              prompt.toolChoice = toolChoice;
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/updateToolChoice"
          );
        },

        updateTool: (promptId: string, toolId: string, tool: Partial<FrontendTool>) => {
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === promptId);
              if (!prompt) return;

              prompt.tools = prompt.tools.map((t) => (t.id === toolId ? { ...t, ...tool } : t));
              prompt.isDirty = !!prompt.version;

              state.mutation.changedAt = now();
            },
            false,
            "playground/updateTool"
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

        extractPromptVariables: (promptId: string, variables: string[]) => {
          const { keywordTracker, keywords } = get();
          set(
            (state) => {
              const prompt = state.prompts.find((prompt) => prompt.id === promptId);
              if (!prompt) return;

              const messageIds = prompt.messages.map((m) => m.id);

              const { keywordTracker: newKeywordTracker, keywords: newKeywords } = cleanupAndRecalculateKeywords(
                state.prompts,
                keywordTracker,
                keywords,
                (tracker) => {
                  if (variables.length === 0) {
                    // Remove all message IDs from this prompt from keyword tracker
                    messageIds.forEach((id) => tracker.delete(id));
                  } else {
                    // Map all variables to all message IDs in this prompt
                    // (Backend doesn't provide per-message mapping, so we associate all variables with all messages)
                    messageIds.forEach((id) => {
                      tracker.set(id, variables);
                    });
                  }
                }
              );

              state.keywordTracker = newKeywordTracker;
              state.keywords = newKeywords;
            },
            false,
            "playground/extractPromptVariables"
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
              const prompt = state.prompts.find((prompt) => prompt.id === promptId);
              if (!prompt) return;

              prompt.running = true;
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
