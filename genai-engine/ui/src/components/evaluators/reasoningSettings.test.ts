import { describe, expect, it } from "vitest";

import { applyReasoningSettings, EMPTY_REASONING_SETTINGS, reasoningSettingsError, reasoningSettingsFromConfig } from "./reasoningSettings";

describe("applyReasoningSettings", () => {
  it("leaves the config out when nothing is set", () => {
    expect(applyReasoningSettings(null, EMPTY_REASONING_SETTINGS, "anthropic", "claude-haiku-4-5")).toBeUndefined();
  });

  it("sends thinking off as an explicit disabled type for Anthropic", () => {
    expect(applyReasoningSettings(null, { ...EMPTY_REASONING_SETTINGS, thinkingMode: "disabled" }, "anthropic", "claude-haiku-4-5")).toEqual({
      thinking: { type: "disabled" },
    });
  });

  it("sends an enabled thinking budget as a number", () => {
    expect(
      applyReasoningSettings(
        null,
        { reasoningEffort: "", thinkingMode: "enabled", budgetTokens: "4096" },
        "bedrock",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
      )
    ).toEqual({
      thinking: { type: "enabled", budget_tokens: 4096 },
    });
  });

  it("drops thinking for providers that don't take it", () => {
    expect(applyReasoningSettings(null, { reasoningEffort: "low", thinkingMode: "disabled", budgetTokens: "2048" }, "openai", "gpt-5-mini")).toEqual({
      reasoning_effort: "low",
    });
  });

  it("keeps the eval's other settings and replaces the reasoning ones", () => {
    const config = { temperature: 0.2, max_tokens: 500, top_p: null, reasoning_effort: "high" as const, thinking: { type: "adaptive" as const } };
    expect(applyReasoningSettings(config, EMPTY_REASONING_SETTINGS, "anthropic", "claude-haiku-4-5")).toEqual({ temperature: 0.2, max_tokens: 500 });
    expect(applyReasoningSettings(config, { ...EMPTY_REASONING_SETTINGS, reasoningEffort: "minimal" }, "anthropic", "claude-haiku-4-5")).toEqual({
      temperature: 0.2,
      max_tokens: 500,
      reasoning_effort: "minimal",
    });
  });
});

describe("thinking support", () => {
  it("sends thinking for Claude on Bedrock and Vertex AI but not for Gemini", () => {
    const off = { ...EMPTY_REASONING_SETTINGS, thinkingMode: "disabled" as const };
    expect(applyReasoningSettings(null, off, "vertex_ai", "claude-sonnet-4-5")).toEqual({ thinking: { type: "disabled" } });
    expect(applyReasoningSettings(null, off, "vertex_ai", "gemini-2.5-flash")).toBeUndefined();
    expect(applyReasoningSettings(null, off, "gemini", "gemini-2.5-flash")).toBeUndefined();
    expect(applyReasoningSettings(null, off, "bedrock", "amazon.nova-pro-v1:0")).toBeUndefined();
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
    expect(applyReasoningSettings(null, settings, "anthropic", "claude-haiku-4-5")).toEqual({
      reasoning_effort: "low",
      thinking: { type: "enabled", budget_tokens: 3000 },
    });
  });
});

describe("reasoningSettingsError", () => {
  it("requires a budget of at least 1024 when thinking is on", () => {
    const on = { reasoningEffort: "" as const, thinkingMode: "enabled" as const };
    expect(reasoningSettingsError({ ...on, budgetTokens: "1000" }, "anthropic", "claude-haiku-4-5")).not.toBeNull();
    expect(reasoningSettingsError({ ...on, budgetTokens: "1.5" }, "anthropic", "claude-haiku-4-5")).not.toBeNull();
    expect(reasoningSettingsError({ ...on, budgetTokens: "1024" }, "anthropic", "claude-haiku-4-5")).toBeNull();
    // The budget isn't sent where thinking isn't, so it can't be wrong there.
    expect(reasoningSettingsError({ ...on, budgetTokens: "" }, "openai", "gpt-5-mini")).toBeNull();
  });
});

describe("always-thinking models", () => {
  it("rejects turning thinking off where the model always thinks", () => {
    const off = { ...EMPTY_REASONING_SETTINGS, thinkingMode: "disabled" as const };
    const none = { ...EMPTY_REASONING_SETTINGS, reasoningEffort: "none" as const };
    expect(reasoningSettingsError(off, "anthropic", "claude-sonnet-5-5")).toMatch(/can't be turned off/);
    expect(reasoningSettingsError(none, "anthropic", "claude-opus-5-5")).toMatch(/can't be turned off/);
    expect(reasoningSettingsError(off, "bedrock", "us.anthropic.claude-fable-5-1")).toMatch(/can't be turned off/);
    expect(reasoningSettingsError(off, "vertex_ai", "claude-opus-5-5@default")).toMatch(/can't be turned off/);
    // Low takes effect there, and off still works on other Claude models.
    expect(reasoningSettingsError({ ...EMPTY_REASONING_SETTINGS, reasoningEffort: "low" }, "anthropic", "claude-sonnet-5-5")).toBeNull();
    expect(reasoningSettingsError(off, "anthropic", "claude-haiku-4-5")).toBeNull();
  });
});
