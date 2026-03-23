import { v4 as uuidv4 } from "uuid";

import {
  MessageType,
  MESSAGE_ROLE_OPTIONS,
  ModelParametersType,
  PlaygroundInitialData,
  PromptAction,
  promptClassificationEnum,
  PromptPlaygroundState,
  PromptType,
  FrontendTool,
} from "./types";
import { generateId, arrayUtils, cleanupAndRecalculateKeywords } from "./utils";
import { computePromptDirtyState } from "./utils/promptSaveState";

import { LLMGetAllMetadataResponse, MessageRole, ToolChoiceEnum, ToolChoice } from "@/lib/api-client/api-client";

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
  id: uuidv4().slice(0, 8),
  classification: promptClassificationEnum.DEFAULT,
  name: "",
  created_at: undefined,
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
  needsSave: false,
  savedSnapshot: null,
  ...overrides,
});

const newPrompt = (): PromptType => createPrompt();

const duplicatePrompt = (original: PromptType): PromptType => {
  const newId = uuidv4().slice(0, 8);

  return createPrompt({
    ...original,
    id: newId,
    name: original.name,
    version: null, // Duplicates are new unsaved prompts
    savedSnapshot: null, // No saved baseline -- treat as new
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
};

/**
 * Recomputes derived dirty fields (isDirty, needsSave) for any prompts
 * whose object reference changed between the previous and new state.
 */
function withDirtyRecompute(prevState: PromptPlaygroundState, newState: PromptPlaygroundState): PromptPlaygroundState {
  if (prevState.prompts === newState.prompts) return newState;

  const recomputedPrompts = newState.prompts.map((prompt, i) => {
    if (prevState.prompts[i] === prompt) return prompt;

    const { isDirty, needsSave } = computePromptDirtyState(prompt);
    if (isDirty === prompt.isDirty && needsSave === prompt.needsSave) return prompt;
    return { ...prompt, isDirty, needsSave };
  });

  return { ...newState, prompts: recomputedPrompts };
}

const promptsReducerInner = (state: PromptPlaygroundState, action: PromptAction) => {
  switch (action.type) {
    case "addPrompt":
      return { ...state, prompts: [...state.prompts, newPrompt()] };
    case "deletePrompt": {
      const { id } = action.payload;
      const index = state.prompts.findIndex((prompt) => prompt.id === id);

      const promptToDelete = state.prompts[index];
      const messageIdsToRemove = promptToDelete ? promptToDelete.messages.map((msg) => msg.id) : [];

      const newPrompts = [...state.prompts.slice(0, index), ...state.prompts.slice(index + 1)];

      const { keywordTracker: newKeywordTracker, keywords: newKeywords } = cleanupAndRecalculateKeywords(
        newPrompts,
        state.keywordTracker,
        state.keywords,
        (tracker) => {
          messageIdsToRemove.forEach((messageId) => {
            tracker.delete(messageId);
          });
        }
      );

      return {
        ...state,
        prompts: newPrompts,
        keywords: newKeywords,
        keywordTracker: newKeywordTracker,
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
      // Strip id and derived fields from payload to prevent manual override
      const { id: _incomingId, isDirty: _d, needsSave: _n, ...cleanPayload } = prompt;
      return {
        ...state,
        prompts: state.prompts.map((p) =>
          p.id === promptId
            ? {
                ...p,
                ...cleanPayload,
                messages: prompt.messages ?? p.messages,
                tools: prompt.tools ?? p.tools,
                modelParameters: prompt.modelParameters ?? p.modelParameters,
                responseFormat: prompt.responseFormat ?? p.responseFormat,
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

          const duplicatedMsg = duplicateMessage(messageToDuplicate);
          const messageIndex = prompt.messages.findIndex((msg) => msg.id === id);

          return {
            ...prompt,
            messages: arrayUtils.duplicateAfter(prompt.messages, messageIndex, duplicatedMsg),
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
    case "editMessageToolCalls": {
      const { parentId, id, toolCalls } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? {
                ...prompt,
                messages: prompt.messages.map((message) => (message.id === id ? { ...message, tool_calls: toolCalls } : message)),
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

      const newKeywordTracker = new Map<string, Array<string>>(state.keywordTracker);

      if (messageKeywords.length === 0) {
        newKeywordTracker.delete(id);
      } else {
        newKeywordTracker.set(id, messageKeywords);
      }

      const inUseKeywords = new Set<string>();
      newKeywordTracker.forEach((keywords) => {
        keywords.forEach((keyword) => inUseKeywords.add(keyword));
      });

      const newKeywords = new Map<string, string>(state.keywords);

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

      return {
        ...state,
        keywords: newKeywords,
        keywordTracker: newKeywordTracker,
      };
    }
    case "extractPromptVariables": {
      const { promptId, variables } = action.payload;

      const prompt = state.prompts.find((p) => p.id === promptId);
      if (!prompt) {
        return state;
      }

      const messageIds = prompt.messages.map((msg) => msg.id);

      const { keywordTracker: newKeywordTracker, keywords: newKeywords } = cleanupAndRecalculateKeywords(
        state.prompts,
        state.keywordTracker,
        state.keywords,
        (tracker) => {
          if (variables.length === 0) {
            messageIds.forEach((id) => tracker.delete(id));
          } else {
            messageIds.forEach((id) => {
              tracker.set(id, variables);
            });
          }
        }
      );

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

          let shouldResetToolChoice = false;
          if (prompt.toolChoice) {
            if (typeof prompt.toolChoice === "object" && "function" in prompt.toolChoice) {
              shouldResetToolChoice = prompt.toolChoice.function?.name === toolToDelete.function.name;
            } else if (typeof prompt.toolChoice === "string") {
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

const promptsReducer = (state: PromptPlaygroundState, action: PromptAction) => {
  const newState = promptsReducerInner(state, action);
  return withDirtyRecompute(state, newState);
};

/**
 * Builds a PromptPlaygroundState from pre-resolved initial data.
 * Used by the inner playground component to initialize useReducer
 * with data that the wrapper already fetched, avoiding hydration effects.
 */
const buildInitialReducerState = (data: PlaygroundInitialData): PromptPlaygroundState => ({
  keywords: data.keywords,
  keywordTracker: new Map<string, Array<string>>(),
  prompts: data.prompts.length > 0 ? data.prompts : [newPrompt()],
  backendPrompts: new Array<LLMGetAllMetadataResponse>(),
});

export { promptsReducer, initialState, buildInitialReducerState };
