import { sessionReplayPlugin } from "@amplitude/plugin-session-replay-browser";

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
  const sampleRate = parseReplaySampleRate(import.meta.env.VITE_AMPLITUDE_REPLAY_SAMPLE_RATE);

  if (sampleRate === null) {
    return null;
  }

  return sessionReplayPlugin({
    sampleRate,
    privacyConfig: { defaultMaskLevel: "conservative" },
  });
}
