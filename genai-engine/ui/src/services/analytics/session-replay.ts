import { sessionReplayPlugin } from "@amplitude/plugin-session-replay-browser";

import { devLog, isAmplitudeDebugEnabled } from "./dev-log";

/**
 * Parse VITE_AMPLITUDE_REPLAY_SAMPLE_RATE. Returns null (replay disabled) for
 * unset, zero, negative, >1, or non-numeric values.
 */
export function parseReplaySampleRate(raw: string | undefined): number | null {
  if (!raw) {
    return null;
  }

  const rate = Number(raw);
  if (!Number.isFinite(rate) || rate <= 0 || rate > 1) {
    return null;
  }

  return rate;
}

/**
 * Build the Amplitude Session Replay plugin, or null when replay is disabled.
 * Masking is "conservative" on purpose: this UI renders customer LLM
 * prompt/response content (traces), which must never appear in recordings.
 */
export function createSessionReplayPlugin(): ReturnType<typeof sessionReplayPlugin> | null {
  const rawSampleRate = import.meta.env.VITE_AMPLITUDE_REPLAY_SAMPLE_RATE;
  const sampleRate = parseReplaySampleRate(rawSampleRate);

  if (sampleRate === null) {
    if (!rawSampleRate) {
      devLog("Amplitude Replay", "Session replay disabled: VITE_AMPLITUDE_REPLAY_SAMPLE_RATE is not set.");
    } else {
      devLog(
        "Amplitude Replay",
        `Session replay disabled: invalid VITE_AMPLITUDE_REPLAY_SAMPLE_RATE ${JSON.stringify(rawSampleRate)} (expected a number in (0, 1]).`,
        undefined,
        true
      );
    }
    return null;
  }

  devLog("Amplitude Replay", `Session replay enabled at sample rate ${sampleRate}.`);

  return sessionReplayPlugin({
    sampleRate,
    privacyConfig: { defaultMaskLevel: "conservative" },
    // Surface the plugin's own session-replay diagnostics in the console
    // only when explicitly enabled via VITE_AMPLITUDE_DEBUG.
    debugMode: isAmplitudeDebugEnabled(),
  });
}
