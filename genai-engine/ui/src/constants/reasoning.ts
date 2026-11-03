import type { ModelProvider, ReasoningEffortEnum } from "@/lib/api-client/api-client";

// Every reasoning_effort value the backend accepts, in strength order.
export const REASONING_EFFORT_OPTIONS: ReasoningEffortEnum[] = ["none", "minimal", "low", "medium", "high", "default"];

// Claude takes `thinking`, so the control is shown for Anthropic and for Claude
// models served through Bedrock or Vertex AI. litellm rejects `thinking` on
// OpenAI and Azure, and maps it on Gemini to whether thoughts are returned, not
// whether the model thinks, so the control would mislead there.
export const takesThinking = (provider: ModelProvider | "", modelName: string): boolean =>
  provider === "anthropic" || ((provider === "bedrock" || provider === "vertex_ai") && modelName.toLowerCase().includes("claude"));

// Anthropic's minimum thinking budget.
export const MIN_THINKING_BUDGET_TOKENS = 1024;

// Claude model families that always think. Mirrors litellm's `thinking_always_on`
// flag (its model cost map, read by AnthropicModelInfo._is_always_on_thinking_model):
// litellm drops thinking "disabled" and reasoning_effort "none" before sending to
// these models, and the backend rejects both when an eval is saved. Matched as
// substrings so Bedrock ("us.anthropic.claude-sonnet-5-5") and Vertex AI
// ("claude-opus-5-5@default") ids match too. Add a family when litellm flags one.
const ALWAYS_THINKING_MODEL_FAMILIES = ["claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5", "claude-mythos"];

export const thinkingAlwaysOn = (modelName: string): boolean => {
  const model = modelName.toLowerCase();
  return ALWAYS_THINKING_MODEL_FAMILIES.some((family) => model.includes(family));
};
