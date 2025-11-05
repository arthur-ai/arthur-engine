import { v4 as uuidv4 } from "uuid";

import { PromptType } from "../types";

import { generateId } from ".";

import { AgenticPrompt } from "@/lib/api-client/api-client";

export const toFrontendPrompt = (backendPrompt: AgenticPrompt): PromptType => ({
  id: `${backendPrompt.name}-${uuidv4()}`,
  classification: "default",
  name: backendPrompt.name,
  created_at: backendPrompt.created_at || undefined,
  modelName: backendPrompt.model_name,
  modelProvider: backendPrompt.model_provider,
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
  toolChoice: backendPrompt.tool_choice || "auto",
  modelParameters: {
    temperature: backendPrompt.temperature,
    top_p: backendPrompt.top_p,
    timeout: backendPrompt.timeout,
    stream: true, // BE doesn't store, default to true
    stream_options: backendPrompt.stream_options,
    max_tokens: backendPrompt.max_tokens,
    max_completion_tokens: backendPrompt.max_completion_tokens,
    frequency_penalty: backendPrompt.frequency_penalty,
    presence_penalty: backendPrompt.presence_penalty,
    stop: backendPrompt.stop,
    seed: backendPrompt.seed,
    reasoning_effort: backendPrompt.reasoning_effort,
    logprobs: backendPrompt.logprobs,
    top_logprobs: backendPrompt.top_logprobs,
    logit_bias: backendPrompt.logit_bias,
    thinking: backendPrompt.thinking,
  },
  runResponse: null,
  responseFormat: backendPrompt.response_format ? JSON.stringify(backendPrompt.response_format) : undefined,
  running: false,
  version: backendPrompt.version || null,
});

export default toFrontendPrompt;
