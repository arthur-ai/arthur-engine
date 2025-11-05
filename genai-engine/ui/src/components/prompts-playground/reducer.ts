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

import { AgenticPromptMetadataResponse, MessageRole, ModelProvider, ToolChoiceEnum, ToolChoice } from "@/lib/api-client/api-client";

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
  id: "-" + uuidv4(), // New prompts get a default id
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
  toolChoice: "auto" as ToolChoiceEnum,
  running: false,
  version: null,
  ...overrides,
});

const newPrompt = (): PromptType => createPrompt();

const duplicatePrompt = (original: PromptType): PromptType => {
  const newId = "-" + uuidv4(); // TODO: overwrite on save

  return createPrompt({
    ...original,
    id: newId,
    name: `${original.name} (Copy)`,
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
  backendPrompts: new Array<AgenticPromptMetadataResponse>(),
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
        prompts: state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, modelProvider } : prompt)),
      };
    }
    case "updatePromptModelName": {
      const { promptId, modelName } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, modelName } : prompt)),
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
                responseFormat: prompt.responseFormat,
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
        prompts: state.prompts.map((prompt) => (prompt.id === parentId ? { ...prompt, messages: [...prompt.messages, newMessage()] } : prompt)),
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
              }
            : prompt
        ),
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
              }
            : prompt
        ),
      };
    }
    case "updateKeywords": {
      const { id, messageKeywords } = action.payload;

      if (messageKeywords.length === 0) {
        // Remove message id from keyword tracker
        state.keywordTracker.delete(id);
      } else {
        // Add or replace keyword array tied to new or existing message id
        state.keywordTracker.set(id, messageKeywords);
      }

      // Create new keywords map. Delete keywords by omitting a copy.
      const newKeywords = new Map<string, string>();
      const newKeywordTracker = new Map<string, Array<string>>(state.keywordTracker);

      // For each keyword array
      newKeywordTracker.forEach((keywords) => {
        // For each keyword in the array
        keywords.forEach((keyword) => {
          // Copy existing value if is exists, otherwise set to empty string
          newKeywords.set(keyword, state.keywords.get(keyword) || "");
        });
      });

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
        prompts: state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, modelParameters } : prompt)),
      };
    }
    case "updateResponseFormat": {
      const { promptId, responseFormat } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) => (prompt.id === promptId ? { ...prompt, responseFormat } : prompt)),
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
          prompt.id === promptId ? { ...prompt, toolChoice: toolChoice as ToolChoiceEnum | ToolChoice } : prompt
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
