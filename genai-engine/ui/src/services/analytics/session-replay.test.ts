import { afterEach, describe, expect, it, vi } from "vitest";

import { createSessionReplayPlugin, parseReplaySampleRate } from "./session-replay";

const sessionReplayPluginMock = vi.hoisted(() => vi.fn(() => ({ name: "session-replay-mock" })));

vi.mock("@amplitude/plugin-session-replay-browser", () => ({
  sessionReplayPlugin: sessionReplayPluginMock,
}));

describe("parseReplaySampleRate", () => {
  it.each([
    [undefined, null],
    ["", null],
    ["0", null],
    ["-0.5", null],
    ["1.5", null],
    ["abc", null],
    ["0.01", 0.01],
    ["1", 1],
  ])("parses %j as %j", (raw, expected) => {
    expect(parseReplaySampleRate(raw)).toBe(expected);
  });
});

describe("createSessionReplayPlugin", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("returns null when VITE_AMPLITUDE_REPLAY_SAMPLE_RATE is unset", () => {
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "");
    expect(createSessionReplayPlugin()).toBeNull();
    expect(sessionReplayPluginMock).not.toHaveBeenCalled();
  });

  it("builds the plugin with conservative masking and debug off by default", () => {
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "0.25");
    expect(createSessionReplayPlugin()).toEqual({ name: "session-replay-mock" });
    expect(sessionReplayPluginMock).toHaveBeenCalledWith({
      sampleRate: 0.25,
      privacyConfig: { defaultMaskLevel: "conservative" },
      debugMode: false,
    });
  });

  it("enables debugMode when VITE_AMPLITUDE_DEBUG is set", () => {
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "0.25");
    vi.stubEnv("VITE_AMPLITUDE_DEBUG", "true");
    createSessionReplayPlugin();
    expect(sessionReplayPluginMock).toHaveBeenCalledWith(expect.objectContaining({ debugMode: true }));
  });

  it("warns when the sample rate is set but invalid", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "2");
    expect(createSessionReplayPlugin()).toBeNull();
    expect(sessionReplayPluginMock).not.toHaveBeenCalled();
    if (import.meta.env.DEV) {
      expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("invalid VITE_AMPLITUDE_REPLAY_SAMPLE_RATE"), undefined);
    }
    warnSpy.mockRestore();
  });
});
