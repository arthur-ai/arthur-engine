/**
 * Whether verbose Amplitude debug output (SDK debug logLevel + Session Replay
 * debugMode) is enabled. Off by default; opt back in by setting
 * VITE_AMPLITUDE_DEBUG to "true" (or "1").
 */
export function isAmplitudeDebugEnabled(): boolean {
  const raw = import.meta.env.VITE_AMPLITUDE_DEBUG;
  return raw === "true" || raw === "1";
}

/** Dev-only console logger for analytics diagnostics. */
export function devLog(category: string, message = "", data?: unknown, warn = false): void {
  if (import.meta.env.DEV) {
    const prefix = category ? `[${category}] ` : "";
    const formattedMessage = `${prefix}${message}`;
    const showData = data !== undefined;

    if (warn) {
      console.warn(formattedMessage, showData ? data : undefined);
    } else {
      console.log(formattedMessage, showData ? data : undefined);
    }
  }
}
