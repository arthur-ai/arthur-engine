import { v4 as uuidv4 } from "uuid";

import {
  MessageType,
  MESSAGE_ROLE_OPTIONS,
  ModelParametersType,
  PromptAction,
  promptClassificationEnum,
  PromptPlaygroundState,
  PromptType,
  FrontendTool,
} from "./types";
import { generateId, arrayUtils } from "./utils";

import { LLMGetAllMetadataResponse, MessageRole, ModelProvider, ToolChoiceEnum, ToolChoice } from "@/lib/api-client/api-client";

/****************************
 * Message factory functions *
 ****************************/
const createMessage = (overrides: Partial<MessageType> = {}): MessageType => ({
  id: generateId("msg"),
  role: MESSAGE_ROLE_OPTIONS[1] as MessageRole,
  content: "",
  disabled: false,
  ...overrides,
});

const newMessage = (role: MessageRole = MESSAGE_ROLE_OPTIONS[1] as MessageRole, content: string = ""): MessageType =>
  createMessage({ role, content });

const duplicateMessage = (original: MessageType): MessageType =>
  createMessage({
    ...original,
    id: generateId("msg"),
  });

const hydrateMessage = (data: Partial<MessageType>): MessageType => createMessage(data);

/***************************
 * Tool factory functions *
 ***************************/
const createTool = (counter: number = 1, overrides: Partial<FrontendTool> = {}): FrontendTool => ({
  id: generateId("tool"),
  function: {
    name: `tool_func_${counter}`,
    description: "description",
    parameters: {
      type: "object",
      properties: {
        tool_arg: {
          type: "string",
          description: null,
          enum: null,
          items: null,
        },
      },
      required: [],
      additionalProperties: null,
    },
  },
  strict: false,
  type: "function",
  ...overrides,
});

/***************************
 * Prompt factory functions *
 ***************************/
const createModelParameters = (overrides: Partial<ModelParametersType> = {}): ModelParametersType => ({
  temperature: null,
  top_p: null,
  timeout: null,
  stream: true,
  stream_options: null,
  max_tokens: null,
  max_completion_tokens: null,
  frequency_penalty: null,
  presence_penalty: null,
  stop: null,
  seed: null,
  reasoning_effort: null,
  logprobs: null,
  top_logprobs: null,
  logit_bias: null,
  thinking: null,
  ...overrides,
});

const createPrompt = (overrides: Partial<PromptType> = {}): PromptType => ({
  id: uuidv4().slice(0, 8), // New prompts get a short 8-character id
  classification: promptClassificationEnum.DEFAULT,
  name: "",
  created_at: undefined, // created on BE
  modelName: "",
  modelProvider: "",
  messages: [newMessage()],
  modelParameters: createModelParameters(),
  runResponse: null,
  responseFormat: undefined,
  tools: [],
  toolChoice: undefined,
  running: false,
  version: null,
  isDirty: false,
  ...overrides,
});

const newPrompt = (): PromptType => createPrompt();

const duplicatePrompt = (original: PromptType): PromptType => {
  const newId = uuidv4().slice(0, 8); // Short 8-character id for duplicates

  return createPrompt({
    ...original,
    id: newId,
    name: original.name, // Preserve original name so it shows in Select Prompt dropdown
    version: original.version, // Preserve version to show which version this is based on
    created_at: undefined,
    messages: original.messages.map(duplicateMessage),
    tools: original.tools.map((tool) => ({
      ...tool,
      id: generateId("tool"),
    })),
  });
};
const hydratePrompt = (data: Partial<PromptType>): PromptType => createPrompt(data);

/****************
 * Reducer Logic *
 ****************/
const initialState: PromptPlaygroundState = {
  keywords: new Map<string, string>(),
  keywordTracker: new Map<string, Array<string>>(),
  prompts: [newPrompt()],
  backendPrompts: new Array<LLMGetAllMetadataResponse>(),
  enabledProviders: new Array<ModelProvider>(),
  availableModels: new Map<ModelProvider, string[]>(),
};

const promptsReducer = (state: PromptPlaygroundState, action: PromptAction) => {
  switch (action.type) {
    case "addPrompt":
      return { ...state, prompts: [...state.prompts, newPrompt()] };
    case "deletePrompt": {
      const { id } = action.payload;
      const index = state.prompts.findIndex((prompt) => prompt.id === id);
      return {
        ...state,
        prompts: [...state.prompts.slice(0, index), ...state.prompts.slice(index + 1)],
      };
    }
    case "duplicatePrompt": {
      const { id } = action.payload;
      const originalIndex = state.prompts.findIndex((prompt) => prompt.id === id);

      const originalPrompt = state.prompts[originalIndex];
      const duplicatedPrompt = duplicatePrompt(originalPrompt);

      return {
        ...state,
        prompts: arrayUtils.duplicateAfter(state.prompts, originalIndex, duplicatedPrompt),
      };
    }
    case "hydratePrompt": {
      const { promptData } = action.payload;
      return {
        ...state,
        prompts: [...state.prompts, hydratePrompt(promptData)],
      };
    }
    case "clearPrompts": {
      return {
        ...state,
        prompts: [],
      };
    }
    case "hydrateNotebookState": {
      const { prompts, keywords } = action.payload;
      return {
        ...state,
        prompts: prompts.length > 0 ? prompts : [newPrompt()],
        keywords,
      };
    }
    case "updatePromptName": {
      const { promptId, name } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, name } : prompt)),
      };
    }
    case "updatePromptProvider": {
      const { promptId, modelProvider } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => {
          if (prompt.id === promptId) {
            const wasChanged = prompt.modelProvider !== modelProvider;
            const shouldMarkDirty = wasChanged && prompt.version;

            return {
              ...prompt,
              modelProvider,
              // Only mark dirty if value actually changed and prompt has a version
              isDirty: shouldMarkDirty ? true : prompt.isDirty,
            };
          }
          return prompt;
        }),
      };
    }
    case "updatePromptModelName": {
      const { promptId, modelName } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => {
          if (prompt.id === promptId) {
            const wasChanged = prompt.modelName !== modelName;
            const shouldMarkDirty = wasChanged && prompt.version;

            return {
              ...prompt,
              modelName,
              // Only mark dirty if value actually changed and prompt has a version
              isDirty: shouldMarkDirty ? true : prompt.isDirty,
            };
          }
          return prompt;
        }),
      };
    }
    case "updatePrompt": {
      const { promptId, prompt } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((p) =>
          p.id === promptId
            ? {
                ...p,
                ...prompt,
                // Ensure required properties are always defined
                messages: prompt.messages ?? p.messages,
                tools: prompt.tools ?? p.tools,
                modelParameters: prompt.modelParameters ?? p.modelParameters,
                responseFormat: prompt.responseFormat ?? p.responseFormat,
                // Explicit isDirty in payload takes precedence, otherwise detect backend load, otherwise preserve existing
                isDirty:
                  prompt.isDirty !== undefined
                    ? prompt.isDirty
                    : prompt.version !== undefined && prompt.messages !== undefined
                      ? false
                      : p.isDirty,
              }
            : p
        ),
      };
    }
    case "updateBackendPrompts": {
      const { prompts } = action.payload;
      return {
        ...state,
        backendPrompts: prompts,
      };
    }
    case "updateProviders": {
      const { providers } = action.payload;
      return {
        ...state,
        enabledProviders: providers as ModelProvider[],
      };
    }
    case "updateAvailableModels": {
      const { availableModels } = action.payload;
      return {
        ...state,
        availableModels,
      };
    }
    case "addMessage": {
      const { parentId } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? { ...prompt, messages: [...prompt.messages, newMessage()], isDirty: prompt.version ? true : false }
            : prompt
        ),
      };
    }
    case "deleteMessage": {
      const { parentId, id } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? {
                ...prompt,
                messages: prompt.messages.filter((msg) => msg.id !== id),
                isDirty: prompt.version ? true : false,
              }
            : prompt
        ),
      };
    }
    case "duplicateMessage": {
      const { id, parentId } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => {
          if (prompt.id !== parentId) return prompt;

          const messageToDuplicate = prompt.messages.find((msg) => msg.id === id);
          if (!messageToDuplicate) return prompt;

          const duplicatedMessage = duplicateMessage(messageToDuplicate);
          const messageIndex = prompt.messages.findIndex((msg) => msg.id === id);

          return {
            ...prompt,
            messages: arrayUtils.duplicateAfter(prompt.messages, messageIndex, duplicatedMessage),
            isDirty: prompt.version ? true : false,
          };
        }),
      };
    }
    case "hydrateMessage": {
      const { parentId, messageData } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? {
                ...prompt,
                messages: [...prompt.messages, hydrateMessage(messageData)],
              }
            : prompt
        ),
      };
    }
    case "editMessage": {
      const { parentId, id, content } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? {
                ...prompt,
                messages: prompt.messages.map((message) => (message.id === id ? { ...message, content } : message)),
                isDirty: prompt.version ? true : false,
              }
            : prompt
        ),
      };
    }
    case "editMessageToolCalls": {
      const { parentId, id, toolCalls } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => {
          if (prompt.id === parentId) {
            const message = prompt.messages.find((m) => m.id === id);

            // Normalize undefined and null to be treated as equivalent (both mean "no tool calls")
            const oldToolCalls = message?.tool_calls ?? null;
            const newToolCalls = toolCalls ?? null;
            const wasChanged = JSON.stringify(oldToolCalls) !== JSON.stringify(newToolCalls);
            const shouldMarkDirty = wasChanged && prompt.version;

            return {
              ...prompt,
              messages: prompt.messages.map((message) => (message.id === id ? { ...message, tool_calls: toolCalls } : message)),
              isDirty: shouldMarkDirty ? true : prompt.isDirty,
            };
          }
          return prompt;
        }),
      };
    }
    case "changeMessageRole": {
      const { parentId, id, role } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? {
                ...prompt,
                messages: prompt.messages.map((message) => (message.id === id ? { ...message, role: role as MessageRole } : message)),
                isDirty: prompt.version ? true : false,
              }
            : prompt
        ),
      };
    }
    case "updateKeywords": {
      const { id, messageKeywords } = action.payload;

      // Create new keyword tracker without mutating state
      const newKeywordTracker = new Map<string, Array<string>>(state.keywordTracker);

      if (messageKeywords.length === 0) {
        // Remove message id from keyword tracker
        newKeywordTracker.delete(id);
      } else {
        // Add or replace keyword array tied to new or existing message id
        newKeywordTracker.set(id, messageKeywords);
      }

      // Collect all keywords that are currently in use across all messages
      const inUseKeywords = new Set<string>();
      newKeywordTracker.forEach((keywords) => {
        keywords.forEach((keyword) => inUseKeywords.add(keyword));
      });

      // Build new keywords map starting with existing keywords to preserve all values
      const newKeywords = new Map<string, string>(state.keywords);

      // Add any new keywords from messages that don't exist yet
      inUseKeywords.forEach((keyword) => {
        if (!newKeywords.has(keyword)) {
          newKeywords.set(keyword, "");
        }
      });

      // Remove keywords that are not in use in any message
      for (const keyword of newKeywords.keys()) {
        if (!inUseKeywords.has(keyword)) {
          newKeywords.delete(keyword);
        }
      }

      return {
        ...state,
        keywords: newKeywords,
        keywordTracker: newKeywordTracker,
      };
    }
    case "updateKeywordValue": {
      const { keyword, value } = action.payload;
      return {
        ...state,
        keywords: new Map(state.keywords).set(keyword, value),
      };
    }
    case "runPrompt": {
      const { promptId } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, running: true, runResponse: null } : prompt)),
      };
    }
    case "updateModelParameters": {
      const { promptId, modelParameters } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === promptId ? { ...prompt, modelParameters, isDirty: prompt.version ? true : false } : prompt
        ),
      };
    }
    case "updateResponseFormat": {
      const { promptId, responseFormat } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === promptId ? { ...prompt, responseFormat, isDirty: prompt.version ? true : false } : prompt
        ),
      };
    }
    case "addTool": {
      const { promptId } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === promptId
            ? {
                ...prompt,
                tools: [...prompt.tools, createTool(prompt.tools.length + 1)],
                isDirty: prompt.version ? true : false,
              }
            : prompt
        ),
      };
    }
    case "deleteTool": {
      const { promptId, toolId } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => {
          if (prompt.id !== promptId) return prompt;

          const toolToDelete = prompt.tools.find((tool) => tool.id === toolId);
          if (!toolToDelete) return prompt;

          // Check if the toolChoice references the tool being deleted
          let shouldResetToolChoice = false;
          if (prompt.toolChoice) {
            if (typeof prompt.toolChoice === "object" && "function" in prompt.toolChoice) {
              // It's a ToolChoice object - check if function name matches
              shouldResetToolChoice = prompt.toolChoice.function?.name === toolToDelete.function.name;
            } else if (typeof prompt.toolChoice === "string") {
              // It's a ToolChoiceEnum or potentially an old tool ID string
              // Check if it matches the tool ID (for backwards compatibility)
              shouldResetToolChoice = prompt.toolChoice === toolId;
            }
          }

          return {
            ...prompt,
            tools: prompt.tools.filter((tool) => tool.id !== toolId),
            toolChoice: shouldResetToolChoice ? ("auto" as ToolChoiceEnum) : prompt.toolChoice,
            isDirty: prompt.version ? true : false,
          };
        }),
      };
    }
    case "updateTool": {
      const { parentId, toolId, tool } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? {
                ...prompt,
                tools: prompt.tools.map((t) => (t.id === toolId ? { ...t, ...tool } : t)),
                isDirty: prompt.version ? true : false,
              }
            : prompt
        ),
      };
    }
    case "updateToolChoice": {
      const { promptId, toolChoice } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === promptId
            ? { ...prompt, toolChoice: toolChoice as ToolChoiceEnum | ToolChoice, isDirty: prompt.version ? true : false }
            : prompt
        ),
      };
    }
    case "moveMessage": {
      const { parentId, fromIndex, toIndex } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? {
                ...prompt,
                messages: arrayUtils.moveItem(prompt.messages, fromIndex, toIndex),
                isDirty: prompt.version ? true : false,
              }
            : prompt
        ),
      };
    }
    default:
      return state;
  }
};

export { promptsReducer, initialState };
