import { describe, expect, it } from "vitest";

import { CLAUDE_HAIKU_4_5, CLAUDE_SONNET_5_5, GPT_4O_MINI, GPT_5_MINI, UNKNOWN_MODEL } from "./reasoningOptionsFixtures.test-utils";
import {
  applyReasoningSettings,
  effortChoices,
  EMPTY_REASONING_SETTINGS,
  reasoningSettingsError,
  reasoningSettingsFromConfig,
  thinkingChoices,
  thinkingShown,
} from "./reasoningSettings";

describe("options from the backend", () => {
  it("offers only what the model accepts", () => {
    expect(effortChoices(GPT_5_MINI)).toEqual(["minimal", "low", "medium", "high"]);
    expect(thinkingShown(GPT_5_MINI)).toBe(false);
    expect(effortChoices(GPT_4O_MINI)).toEqual([]);
    expect(thinkingChoices(CLAUDE_SONNET_5_5)).toEqual(["adaptive", "enabled"]);
    expect(thinkingChoices(CLAUDE_HAIKU_4_5)).toEqual(["disabled", "adaptive", "enabled"]);
  });

  it("offers everything but 'default' when litellm doesn't know the model", () => {
    expect(effortChoices(UNKNOWN_MODEL)).toEqual(["none", "minimal", "low", "medium", "high"]);
    expect(effortChoices(CLAUDE_HAIKU_4_5)).toEqual(["none", "minimal", "low", "medium", "high"]);
    expect(thinkingShown(UNKNOWN_MODEL)).toBe(true);
    expect(thinkingChoices(UNKNOWN_MODEL)).toEqual(["disabled", "adaptive", "enabled"]);
  });
});

describe("applyReasoningSettings", () => {
  it("leaves the config out when nothing is set", () => {
    expect(applyReasoningSettings(null, EMPTY_REASONING_SETTINGS, CLAUDE_HAIKU_4_5)).toBeUndefined();
  });

  it("sends thinking off as an explicit disabled type", () => {
    expect(applyReasoningSettings(null, { ...EMPTY_REASONING_SETTINGS, thinkingMode: "disabled" }, CLAUDE_HAIKU_4_5)).toEqual({
      thinking: { type: "disabled" },
    });
  });

  it("sends an enabled thinking budget as a number", () => {
    expect(applyReasoningSettings(null, { reasoningEffort: "", thinkingMode: "enabled", budgetTokens: "4096" }, CLAUDE_HAIKU_4_5)).toEqual({
      thinking: { type: "enabled", budget_tokens: 4096 },
    });
  });

  it("drops thinking for models that don't take it", () => {
    expect(applyReasoningSettings(null, { reasoningEffort: "low", thinkingMode: "disabled", budgetTokens: "2048" }, GPT_5_MINI)).toEqual({
      reasoning_effort: "low",
    });
  });

  it("keeps the eval's other settings and replaces the reasoning ones", () => {
    const config = { temperature: 0.2, max_tokens: 500, top_p: null, reasoning_effort: "high" as const, thinking: { type: "adaptive" as const } };
    expect(applyReasoningSettings(config, EMPTY_REASONING_SETTINGS, CLAUDE_HAIKU_4_5)).toEqual({ temperature: 0.2, max_tokens: 500 });
    expect(applyReasoningSettings(config, { ...EMPTY_REASONING_SETTINGS, reasoningEffort: "minimal" }, CLAUDE_HAIKU_4_5)).toEqual({
      temperature: 0.2,
      max_tokens: 500,
      reasoning_effort: "minimal",
    });
  });
});

describe("reasoningSettingsFromConfig", () => {
  it("reads unset settings as the provider default", () => {
    expect(reasoningSettingsFromConfig(undefined)).toEqual(EMPTY_REASONING_SETTINGS);
    expect(reasoningSettingsFromConfig({ temperature: 0 })).toEqual(EMPTY_REASONING_SETTINGS);
  });

  it("round-trips saved settings", () => {
    const settings = reasoningSettingsFromConfig({ reasoning_effort: "low", thinking: { type: "enabled", budget_tokens: 3000 } });
    expect(settings).toEqual({ reasoningEffort: "low", thinkingMode: "enabled", budgetTokens: "3000" });
    expect(applyReasoningSettings(null, settings, CLAUDE_HAIKU_4_5)).toEqual({
      reasoning_effort: "low",
      thinking: { type: "enabled", budget_tokens: 3000 },
    });
  });
});

describe("reasoningSettingsError", () => {
  const effort = (reasoningEffort: "none" | "minimal" | "low") => ({ ...EMPTY_REASONING_SETTINGS, reasoningEffort });
  const off = { ...EMPTY_REASONING_SETTINGS, thinkingMode: "disabled" as const };

  it("rejects an effort the model refuses, naming the allowed ones", () => {
    expect(reasoningSettingsError(effort("none"), GPT_5_MINI)).toBe(
      'Reasoning effort "none" isn\'t supported by this model. Allowed: "minimal", "low", "medium", "high".'
    );
    expect(reasoningSettingsError(effort("low"), GPT_4O_MINI)).toBe("This model doesn't take a reasoning effort.");
    expect(reasoningSettingsError(effort("minimal"), GPT_5_MINI)).toBeNull();
  });

  it("points always-thinking models to effort low", () => {
    expect(reasoningSettingsError(off, CLAUDE_SONNET_5_5)).toMatch(/can't be turned off.*reasoning effort low/);
    expect(reasoningSettingsError(effort("none"), CLAUDE_SONNET_5_5)).toMatch(/can't be turned off/);
    expect(reasoningSettingsError(off, CLAUDE_HAIKU_4_5)).toBeNull();
  });

  it("passes anything for models litellm doesn't know", () => {
    expect(reasoningSettingsError({ ...off, reasoningEffort: "none" }, UNKNOWN_MODEL)).toBeNull();
  });

  it("requires a budget of at least 1024 when thinking is on", () => {
    const on = { reasoningEffort: "" as const, thinkingMode: "enabled" as const };
    expect(reasoningSettingsError({ ...on, budgetTokens: "1000" }, CLAUDE_HAIKU_4_5)).not.toBeNull();
    expect(reasoningSettingsError({ ...on, budgetTokens: "1.5" }, CLAUDE_HAIKU_4_5)).not.toBeNull();
    expect(reasoningSettingsError({ ...on, budgetTokens: "1024" }, CLAUDE_HAIKU_4_5)).toBeNull();
  });
});
