import type { ModelReasoningOptions } from "@/lib/api-client/api-client";

// Shapes GET /api/v1/model_providers/{provider}/reasoning_options returns.
export const GPT_5_MINI: ModelReasoningOptions = {
  provider: "openai",
  model_name: "gpt-5-mini",
  reasoning_efforts: ["minimal", "low", "medium", "high"],
  thinking: { supported: false, can_disable: false, types: [] },
};

export const GPT_4O_MINI: ModelReasoningOptions = {
  provider: "openai",
  model_name: "gpt-4o-mini",
  reasoning_efforts: [],
  thinking: { supported: false, can_disable: false, types: [] },
};

export const CLAUDE_HAIKU_4_5: ModelReasoningOptions = {
  provider: "anthropic",
  model_name: "claude-haiku-4-5",
  reasoning_efforts: null,
  thinking: { supported: true, can_disable: true, types: ["enabled", "adaptive", "disabled"] },
};

export const CLAUDE_SONNET_5_5: ModelReasoningOptions = {
  provider: "anthropic",
  model_name: "claude-sonnet-5-5",
  reasoning_efforts: ["minimal", "low", "medium", "high"],
  thinking: { supported: true, can_disable: false, types: ["enabled", "adaptive"] },
};

export const UNKNOWN_MODEL: ModelReasoningOptions = {
  provider: "azure",
  model_name: "my-prod-deployment",
  reasoning_efforts: null,
  thinking: { supported: null, can_disable: null, types: null },
};
