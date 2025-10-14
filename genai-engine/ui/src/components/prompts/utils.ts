import { v4 as uuidv4 } from "uuid";

import { PromptType } from "./types";

import { AgenticPrompt } from "@/lib/api-client/api-client";

export const toBackendPrompt = (prompt: PromptType): AgenticPrompt => ({
  name: prompt.name,
  model_name: prompt.modelName,
  model_provider: prompt.provider,
  messages: prompt.messages.map((msg) => ({
    role: msg.role,
    content: msg.content,
  })),
  tools: prompt.tools.map((tool) => ({
    type: tool.type,
    function: tool.function,
  })),
  tool_choice: prompt.toolChoice,
  temperature: prompt.modelParameters.temperature,
  top_p: prompt.modelParameters.top_p,
  timeout: prompt.modelParameters.timeout,
  stream: prompt.modelParameters.stream,
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

export const toFrontendPrompt = (backendPrompt: AgenticPrompt): PromptType => ({
  id: `${backendPrompt.name}-${uuidv4()}`,
  classification: "default",
  name: backendPrompt.name,
  modelName: backendPrompt.model_name,
  provider: backendPrompt.model_provider,
  messages: backendPrompt.messages.map((msg, index) => ({
    id: `msg-${backendPrompt.name}-${index}-${Date.now()}`,
    role: msg.role,
    content: msg.content,
    disabled: false,
  })),
  tools: (backendPrompt.tools || []).map((tool, index) => ({
    id: `tool-${backendPrompt.name}-${index}-${Date.now()}`,
    type: "function",
    function: tool.function || tool,
  })),
  toolChoice:
    typeof backendPrompt.tool_choice === "string"
      ? backendPrompt.tool_choice
      : "auto",
  modelParameters: {
    temperature: backendPrompt.temperature ?? 1,
    top_p: backendPrompt.top_p ?? 1,
    timeout: backendPrompt.timeout,
    stream: backendPrompt.stream ?? false,
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
