import { MIN_THINKING_BUDGET_TOKENS, takesThinking } from "@/constants/reasoning";
import type { AnthropicThinkingParamInput, Eval, LLMRequestConfigSettings, ModelProvider, ReasoningEffortEnum } from "@/lib/api-client/api-client";

// "" leaves the setting out of the eval's config, so the provider's default (or
// the model's own default) applies.
export type ThinkingMode = "" | "disabled" | "adaptive" | "enabled";

export interface ReasoningSettings {
  reasoningEffort: ReasoningEffortEnum | "";
  thinkingMode: ThinkingMode;
  budgetTokens: string;
}

export const DEFAULT_THINKING_BUDGET_TOKENS = 2048;

export const EMPTY_REASONING_SETTINGS: ReasoningSettings = {
  reasoningEffort: "",
  thinkingMode: "",
  budgetTokens: String(DEFAULT_THINKING_BUDGET_TOKENS),
};

export const reasoningSettingsFromConfig = (config: Eval["config"]): ReasoningSettings => {
  const reasoningEffort = (config?.reasoning_effort as ReasoningEffortEnum | null | undefined) ?? "";
  const thinking = config?.thinking as AnthropicThinkingParamInput | null | undefined;
  return {
    reasoningEffort,
    thinkingMode: thinking?.type ?? "",
    budgetTokens: String(thinking?.budget_tokens ?? DEFAULT_THINKING_BUDGET_TOKENS),
  };
};

export const reasoningSettingsError = (settings: ReasoningSettings, provider: ModelProvider | "", modelName: string): string | null => {
  if (!takesThinking(provider, modelName) || settings.thinkingMode !== "enabled") return null;
  const budget = Number(settings.budgetTokens);
  if (!Number.isInteger(budget) || budget < MIN_THINKING_BUDGET_TOKENS) {
    return `Thinking budget must be a whole number of at least ${MIN_THINKING_BUDGET_TOKENS} tokens.`;
  }
  return null;
};

const toThinking = (settings: ReasoningSettings): AnthropicThinkingParamInput | null => {
  switch (settings.thinkingMode) {
    case "":
      return null;
    case "enabled":
      return { type: "enabled", budget_tokens: Number(settings.budgetTokens) };
    default:
      return { type: settings.thinkingMode };
  }
};

/**
 * The eval config to save: the existing config's other settings, with
 * reasoning_effort and thinking replaced by the chosen ones. Unset settings are
 * left out rather than sent as null. Returns undefined when nothing is left.
 */
export const applyReasoningSettings = (
  config: Eval["config"],
  settings: ReasoningSettings,
  provider: ModelProvider | "",
  modelName: string
): LLMRequestConfigSettings | undefined => {
  const next: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(config ?? {})) {
    if (value !== null && value !== undefined && key !== "reasoning_effort" && key !== "thinking") {
      next[key] = value;
    }
  }
  if (settings.reasoningEffort) {
    next.reasoning_effort = settings.reasoningEffort;
  }
  const thinking = takesThinking(provider, modelName) ? toThinking(settings) : null;
  if (thinking) {
    next.thinking = thinking;
  }
  return Object.keys(next).length > 0 ? (next as LLMRequestConfigSettings) : undefined;
};
