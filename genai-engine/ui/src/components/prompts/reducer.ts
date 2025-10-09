import { v4 as uuidv4 } from "uuid";

import {
  MessageType,
  messageRoleEnum,
  ModelParametersType,
  PromptAction,
  promptClassificationEnum,
  PromptPlaygroundState,
  PromptType,
  providerEnum,
} from "./types";

const TEMP_ID = "user-defined-name-timestamp";

const arrayUtils = {
  //   insertAt: <T>(array: T[], index: number, item: T): T[] => [
  //     ...array.slice(0, index),
  //     item,
  //     ...array.slice(index),
  //   ],

  // TODO
  moveItem: <T>(array: T[], fromIndex: number, toIndex: number): T[] => {
    const newArray = [...array];
    const [item] = newArray.splice(fromIndex, 1);
    newArray.splice(toIndex, 0, item);
    return newArray;
  },

  duplicateAfter: <T>(array: T[], originalIndex: number, duplicate: T): T[] => [
    ...array.slice(0, originalIndex + 1),
    duplicate,
    ...array.slice(originalIndex + 1),
  ],
};

const generateId = () => {
  return TEMP_ID + uuidv4();
};

/****************************
 * Message factory functions *
 ****************************/
const createMessage = (overrides: Partial<MessageType> = {}): MessageType => ({
  id: generateId(),
  role: messageRoleEnum.USER,
  content: "Change me",
  disabled: false,
  ...overrides,
});

const newMessage = (
  role: string = messageRoleEnum.USER,
  content: string = "Change me"
): MessageType => createMessage({ role, content });

const duplicateMessage = (original: MessageType): MessageType =>
  createMessage({
    ...original,
    id: generateId(),
  });

const hydrateMessage = (data: Partial<MessageType>): MessageType =>
  createMessage(data);

/***************************
 * Prompt factory functions *
 ***************************/
const createModelParameters = (
  overrides: Partial<ModelParametersType> = {}
): ModelParametersType => ({
  temperature: 1,
  top_p: 1,
  timeout: null,
  stream: false,
  stream_options: null,
  max_tokens: null,
  max_completion_tokens: null,
  frequency_penalty: 0,
  presence_penalty: 0,
  stop: null,
  seed: null,
  reasoning_effort: "",
  logprobs: null,
  top_logprobs: null,
  logit_bias: null,
  thinking: null,
  ...overrides,
});

const createPrompt = (overrides: Partial<PromptType> = {}): PromptType => ({
  id: generateId(),
  classification: promptClassificationEnum.DEFAULT,
  name: "",
  modelName: "",
  provider: providerEnum.OPENAI,
  messages: [newMessage()],
  modelParameters: createModelParameters(),
  outputField: "",
  responseFormat: null,
  ...overrides,
});

const newPrompt = (provider: string = providerEnum.OPENAI): PromptType =>
  createPrompt({ provider });

const duplicatePrompt = (original: PromptType): PromptType =>
  createPrompt({
    ...original,
    id: generateId(),
    name: `${original.name} (Copy)`,
  });

const hydratePrompt = (data: Partial<PromptType>): PromptType =>
  createPrompt(data);

/****************
 * Reducer Logic *
 ****************/
const initialState: PromptPlaygroundState = {
  keywords: new Map<string, string>(),
  keywordTracker: new Map<string, Array<string>>(),
  prompts: [newPrompt()],
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
        prompts: [
          ...state.prompts.slice(0, index),
          ...state.prompts.slice(index + 1),
        ],
      };
    }
    case "duplicatePrompt": {
      const { id } = action.payload;
      const originalIndex = state.prompts.findIndex(
        (prompt) => prompt.id === id
      );

      const originalPrompt = state.prompts[originalIndex];
      const duplicatedPrompt = duplicatePrompt(originalPrompt);

      return {
        ...state,
        prompts: arrayUtils.duplicateAfter(
          state.prompts,
          originalIndex,
          duplicatedPrompt
        ),
      };
    }
    case "hydratePrompt": {
      const { promptData } = action.payload;
      return {
        ...state,
        prompts: [...state.prompts, hydratePrompt(promptData)],
      };
    }
    case "addMessage": {
      const { parentId } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === parentId
            ? { ...prompt, messages: [...prompt.messages, newMessage()] }
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

          const messageToDuplicate = prompt.messages.find(
            (msg) => msg.id === id
          );
          if (!messageToDuplicate) return prompt;

          const duplicatedMessage = duplicateMessage(messageToDuplicate);
          const messageIndex = prompt.messages.findIndex(
            (msg) => msg.id === id
          );

          return {
            ...prompt,
            messages: arrayUtils.duplicateAfter(
              prompt.messages,
              messageIndex,
              duplicatedMessage
            ),
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
                messages: prompt.messages.map((message) =>
                  message.id === id ? { ...message, content } : message
                ),
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
                messages: prompt.messages.map((message) =>
                  message.id === id ? { ...message, role } : message
                ),
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
      const newKeywordTracker = new Map<string, Array<string>>(
        state.keywordTracker
      );

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
    case "updateModelParameters": {
      const { promptId, modelParameters } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === promptId ? { ...prompt, modelParameters } : prompt
        ),
      };
    }
    case "updateResponseFormat": {
      const { promptId, responseFormat } = action.payload;
      return {
        ...state,
        prompts: state.prompts.map((prompt) =>
          prompt.id === promptId ? { ...prompt, responseFormat } : prompt
        ),
      };
    }
    default:
      return state;
  }
};

export { promptsReducer, initialState };
