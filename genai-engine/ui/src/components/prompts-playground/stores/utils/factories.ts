import { v4 as uuidv4 } from "uuid";

import { MESSAGE_ROLE_OPTIONS, MessageType, ModelParametersType, promptClassificationEnum, PromptType } from "../../types";
import { MessageRole } from "@/lib/api-client/api-client";
import { generateId } from "../../utils";

export const createPrompt = (overrides: Partial<PromptType> = {}): PromptType => ({
  id: uuidv4().slice(0, 8), // New prompts get a short 8-character id
  classification: promptClassificationEnum.DEFAULT,
  name: "",
  modelName: "",
  modelProvider: "",
  messages: [],
  tools: [],
  modelParameters: createModelParameters(),
  created_at: undefined, // created on BE
  toolChoice: undefined,
  responseFormat: undefined,
  runResponse: null,
  running: false,
  version: null,
  isDirty: false,
  ...overrides,
});

export const createModelParameters = (): ModelParametersType => ({
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
});

export const createMessage = (overrides: Partial<MessageType> = {}): MessageType => ({
  id: generateId("msg"),
  role: MESSAGE_ROLE_OPTIONS[1] as MessageRole,
  content: "",
  disabled: false,
  ...overrides,
});

export const newMessage = (role: MessageRole = MESSAGE_ROLE_OPTIONS[1] as MessageRole, content: string = ""): MessageType =>
  createMessage({ role, content });

export const duplicatePrompt = (original: PromptType): PromptType => {
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

export const duplicateMessage = (original: MessageType): MessageType =>
  createMessage({
    ...original,
    id: generateId("msg"),
  });
