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
  toolChoice: backendPrompt.config?.tool_choice ?? undefined,
  modelParameters: {
    temperature: backendPrompt.config?.temperature,
    top_p: backendPrompt.config?.top_p,
    timeout: backendPrompt.config?.timeout,
    stream: true, // BE doesn't store, default to true
    stream_options: backendPrompt.config?.stream_options,
    max_tokens: backendPrompt.config?.max_tokens,
    max_completion_tokens: backendPrompt.config?.max_completion_tokens,
    frequency_penalty: backendPrompt.config?.frequency_penalty,
    presence_penalty: backendPrompt.config?.presence_penalty,
    stop: backendPrompt.config?.stop,
    seed: backendPrompt.config?.seed,
    reasoning_effort: backendPrompt.config?.reasoning_effort,
    logprobs: backendPrompt.config?.logprobs,
    top_logprobs: backendPrompt.config?.top_logprobs,
    logit_bias: backendPrompt.config?.logit_bias,
    thinking: backendPrompt.config?.thinking,
  },
  runResponse: null,
  responseFormat: backendPrompt.config?.response_format ? JSON.stringify(backendPrompt.config.response_format, null, 2) : undefined,
  running: false,
  version: backendPrompt.version || null,
  isDirty: false, // Prompts loaded from backend should not be marked as dirty
});

export default toFrontendPrompt;
