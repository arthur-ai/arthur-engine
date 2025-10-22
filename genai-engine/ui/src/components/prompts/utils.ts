import { v4 as uuidv4 } from "uuid";

import { PromptType } from "./types";

import {
  AgenticPrompt,
  AgenticPromptBaseConfig,
  ToolChoiceEnum,
  ModelProvider,
} from "@/lib/api-client/api-client";

export const arrayUtils = {
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

export const generateId = (type: "msg" | "tool") => {
  return type + "-" + uuidv4();
};

export const toBackendPrompt = (prompt: PromptType): AgenticPrompt => ({
  name: prompt.name,
  model_name: prompt.modelName,
  model_provider: prompt.provider as ModelProvider,
  messages: prompt.messages.map((msg) => ({
    role: msg.role,
    content: msg.content,
    tool_call_id: null,
    tool_calls: null,
  })),
  tools: prompt.tools.map((tool) => ({
    function: {
      name: tool.function.name,
      description: tool.function.description,
      parameters: tool.function.parameters,
    },
    strict: tool.strict,
    type: tool.type,
  })),
  tool_choice: prompt.toolChoice,
  temperature: prompt.modelParameters.temperature,
  top_p: prompt.modelParameters.top_p,
  timeout: prompt.modelParameters.timeout,
  stream_options: prompt.modelParameters.stream_options,
  max_tokens: prompt.modelParameters.max_tokens,
  max_completion_tokens: prompt.modelParameters.max_completion_tokens,
  frequency_penalty: prompt.modelParameters.frequency_penalty,
  presence_penalty: prompt.modelParameters.presence_penalty,
  stop: prompt.modelParameters.stop,
  seed: prompt.modelParameters.seed,
  reasoning_effort: prompt.modelParameters.reasoning_effort,
  logprobs: prompt.modelParameters.logprobs,
  top_logprobs: prompt.modelParameters.top_logprobs,
  logit_bias: prompt.modelParameters.logit_bias,
  thinking: prompt.modelParameters.thinking,
  response_format: prompt.responseFormat
    ? JSON.parse(prompt.responseFormat)
    : null,
});

export const toBackendPromptBaseConfig = (
  prompt: PromptType
): AgenticPromptBaseConfig => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { name, ...rest } = toBackendPrompt(prompt);
  return rest;
};

export const toFrontendPrompt = (backendPrompt: AgenticPrompt): PromptType => ({
  id: `${backendPrompt.name}-${new Date(backendPrompt.created_at ?? Date.now()).getTime()}`,
  classification: "default",
  name: backendPrompt.name,
  created_at: backendPrompt.created_at || undefined,
  modelName: backendPrompt.model_name,
  provider: backendPrompt.model_provider,
  messages: backendPrompt.messages.map((msg) => ({
    id: `msg-${uuidv4()}`,
    role: msg.role,
    content: msg.content,
    disabled: false,
  })),
  tools: (backendPrompt.tools || []).map((tool) => ({
    id: generateId("tool"),
    function: {
      name: tool.function.name,
      description: tool.function.description,
      parameters: tool.function.parameters,
    },
    strict: tool.strict,
    type: tool.type,
  })),
  toolChoice: (backendPrompt.tool_choice as ToolChoiceEnum) || "auto",
  modelParameters: {
    temperature: backendPrompt.temperature ?? 1,
    top_p: backendPrompt.top_p ?? 1,
    timeout: backendPrompt.timeout,
    stream_options: backendPrompt.stream_options,
    max_tokens: backendPrompt.max_tokens,
    max_completion_tokens: backendPrompt.max_completion_tokens,
    frequency_penalty: backendPrompt.frequency_penalty ?? 0,
    presence_penalty: backendPrompt.presence_penalty ?? 0,
    stop: backendPrompt.stop,
    seed: backendPrompt.seed,
    reasoning_effort: backendPrompt.reasoning_effort,
    logprobs: backendPrompt.logprobs,
    top_logprobs: backendPrompt.top_logprobs,
    logit_bias: backendPrompt.logit_bias,
    thinking: backendPrompt.thinking,
  },
  outputField: "",
  responseFormat: backendPrompt.response_format
    ? JSON.stringify(backendPrompt.response_format)
    : undefined,
});
