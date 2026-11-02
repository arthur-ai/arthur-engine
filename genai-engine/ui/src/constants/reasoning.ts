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
