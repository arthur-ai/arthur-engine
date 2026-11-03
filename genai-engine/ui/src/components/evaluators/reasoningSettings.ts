import { MIN_THINKING_BUDGET_TOKENS, REASONING_EFFORT_OPTIONS } from "@/constants/reasoning";
import type {
  AnthropicThinkingParamInput,
  Eval,
  LLMRequestConfigSettings,
  ModelReasoningOptions,
  ModelThinkingOptionsTypesEnum,
  ReasoningEffortEnum,
} from "@/lib/api-client/api-client";

// "" leaves the setting out of the eval's config, so the provider's default (or
// the model's own default) applies.
export type ThinkingMode = "" | ModelThinkingOptionsTypesEnum;

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

const ALL_THINKING_TYPES: ModelThinkingOptionsTypesEnum[] = ["disabled", "adaptive", "enabled"];

// Null fields in the options mean litellm doesn't know the model, and the backend
// sends whatever is set, so every choice is offered. "default" means the same as
// leaving the effort unset, so it is never offered.
export const effortChoices = (options: ModelReasoningOptions | undefined): ReasoningEffortEnum[] =>
  (options?.reasoning_efforts ?? REASONING_EFFORT_OPTIONS).filter((effort) => effort !== "default");

export const thinkingShown = (options: ModelReasoningOptions | undefined): boolean => options?.thinking.supported !== false;

export const thinkingChoices = (options: ModelReasoningOptions | undefined): ModelThinkingOptionsTypesEnum[] => {
  const allowed = options?.thinking.types ?? ALL_THINKING_TYPES;
  return ALL_THINKING_TYPES.filter((type) => allowed.includes(type));
};

// The model takes thinking but "disabled" wouldn't turn it off: Claude models that
// always think, and non-Claude models where litellm only maps a thinking budget.
export const thinkingCannotBeDisabled = (options: ModelReasoningOptions | undefined): boolean =>
  options?.thinking.supported === true && options.thinking.can_disable === false;

const quoted = (values: string[]) => values.map((value) => `"${value}"`).join(", ");

export const reasoningSettingsFromConfig = (config: Eval["config"]): ReasoningSettings => {
  const reasoningEffort = (config?.reasoning_effort as ReasoningEffortEnum | null | undefined) ?? "";
  const thinking = config?.thinking as AnthropicThinkingParamInput | null | undefined;
  return {
    reasoningEffort,
    thinkingMode: thinking?.type ?? "",
    budgetTokens: String(thinking?.budget_tokens ?? DEFAULT_THINKING_BUDGET_TOKENS),
  };
};

export const thinkingOffHint = (options: ModelReasoningOptions | undefined): string =>
  "Thinking can't be turned off for this model." +
  (effortChoices(options).includes("low") ? " Use reasoning effort low to keep thinking to a minimum." : "");

/** Why the settings won't work on the selected model, mirroring the backend's save check. */
export const reasoningSettingsError = (settings: ReasoningSettings, options: ModelReasoningOptions | undefined): string | null => {
  const efforts = effortChoices(options);
  if (settings.reasoningEffort && !efforts.includes(settings.reasoningEffort)) {
    if (settings.reasoningEffort === "none" && thinkingCannotBeDisabled(options)) return thinkingOffHint(options);
    return efforts.length > 0
      ? `Reasoning effort "${settings.reasoningEffort}" isn't supported by this model. Allowed: ${quoted(efforts)}.`
      : "This model doesn't take a reasoning effort.";
  }
  if (!thinkingShown(options) || settings.thinkingMode === "") return null;
  const types = thinkingChoices(options);
  if (!types.includes(settings.thinkingMode)) {
    return settings.thinkingMode === "disabled" ? thinkingOffHint(options) : `Thinking "${settings.thinkingMode}" isn't supported by this model.`;
  }
  if (settings.thinkingMode === "enabled") {
    const budget = Number(settings.budgetTokens);
    if (!Number.isInteger(budget) || budget < MIN_THINKING_BUDGET_TOKENS) {
      return `Thinking budget must be a whole number of at least ${MIN_THINKING_BUDGET_TOKENS} tokens.`;
    }
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
 * left out rather than sent as null, and thinking is left out for models that
 * don't take it. Returns undefined when nothing is left.
 */
export const applyReasoningSettings = (
  config: Eval["config"],
  settings: ReasoningSettings,
  options: ModelReasoningOptions | undefined
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
  const thinking = thinkingShown(options) ? toThinking(settings) : null;
  if (thinking) {
    next.thinking = thinking;
  }
  return Object.keys(next).length > 0 ? (next as LLMRequestConfigSettings) : undefined;
};
