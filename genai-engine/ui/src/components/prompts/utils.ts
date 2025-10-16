import { v4 as uuidv4 } from "uuid";

import { PromptType } from "./types";

import {
  AgenticPrompt,
  AgenticPromptBaseConfig,
  ToolChoiceEnum,
} from "@/lib/api-client/api-client";

/**
 *
 * @param concatenatedName name + timestamp
 * @returns a tuple of extracted [name, timestamp]
 */
export const extractName = (concatenatedName: string): [string, string] => {
  // Check if the name contains a timestamp pattern (ends with -{number})
  const timestampPattern = /^(.+)-(\d+)$/;
  const match = concatenatedName.match(timestampPattern);

  if (match) {
    // Valid format: extract the base name and timestamp
    const [, name, timestamp] = match;
    return [name, timestamp];
  } else {
    // Fallback: No name, so the concatenatedName is the timestamp "-timestamp"
    return [concatenatedName, ""];
  }
};

// Helper function to validate and extract name from backend prompt name
const extractNameFromBackend = (backendName: string): string => {
  // Check if the name contains a timestamp pattern (ends with -{number})
  const timestampPattern = /^(.+)-(\d+)$/;
  const match = backendName.match(timestampPattern);

  if (match) {
    // Valid format: extract the base name
    return match[1];
  } else {
    // Fallback: treat the entire name as the base name and add current timestamp
    return backendName;
  }
};

export const toBackendPrompt = (prompt: PromptType): AgenticPrompt => ({
  name: prompt.name,
  model_name: prompt.modelName,
  model_provider: prompt.provider,
  messages: prompt.messages.map((msg) => ({
    role: msg.role,
    content: msg.content,
    tool_call_id: null,
    tool_calls: null,
  })),
  tools: prompt.tools.map((tool) => ({
    name: tool.name,
    description: tool.description,
    function_definition: tool.function_definition,
    strict: tool.strict,
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

export const toFrontendPrompt = (backendPrompt: AgenticPrompt): PromptType => {
  const baseName = extractNameFromBackend(backendPrompt.name);

  return {
    id: backendPrompt.name, // TODO: this will have to be name + backend timestamp
    classification: "default",
    name: baseName, // Extract just the base name for display
    modelName: backendPrompt.model_name,
    provider: backendPrompt.model_provider,
    messages: backendPrompt.messages.map((msg) => ({
      id: `msg-${uuidv4()}`,
      role: msg.role,
      content: msg.content,
      disabled: false,
    })),
    tools: (backendPrompt.tools || []).map((tool) => ({
      id: `tool-${uuidv4()}`,
      name: tool.name,
      description: tool.description,
      function_definition: tool.function_definition,
      strict: tool.strict,
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
  };
};
