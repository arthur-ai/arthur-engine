import * as amplitude from "@amplitude/analytics-browser";

let isInitialized = false;

export const EVENT_NAMES = {
  // Authentication events
  SESSION_RESTORED: "Session Restored",
  TOKEN_VALIDATION_FAILED: "Token Validation Failed",
  AUTH_INITIALIZATION_FAILED: "Auth Initialization Failed",
  LOGIN: "Login",
  LOGIN_FAILED: "Login Failed",
  LOGOUT: "Logout",
  // Prompts Playground events
  RUN_ALL_PROMPTS: "Run All Prompts",
} as const;

/**
 * Logs a message only in development mode.
 * @param category - Optional category prefix (e.g., "Amplitude", "API", "Auth")
 * @param message - The message to log
 * @param data - Optional additional data to log
 * @param warn - Whether to log as a warning
 */
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

/**
 * Initialize Amplitude SDK with API key from environment variables.
 * This should be called once at app startup.
 */
export function initAmplitude(): void {
  const apiKey = import.meta.env.VITE_AMPLITUDE_TOKEN;

  if (!apiKey) {
    console.warn("VITE_AMPLITUDE_TOKEN not set. Amplitude tracking will be disabled.");
    return;
  }

  try {
    // True value tracks Page Views, Sessions, File Downloads, and Form Interactions
    amplitude.init(apiKey, {
      defaultTracking: false,
    });
    isInitialized = true;
  } catch (error) {
    console.error("Failed to initialize Amplitude:", error);
  }
}

/**
 * Track an event in Amplitude.
 * @param eventName - Name of the event to track
 * @param eventProperties - Optional properties to attach to the event
 */
export function track(eventName: string, eventProperties?: Record<string, unknown>): void {
  if (!isInitialized) {
    return;
  }

  try {
    amplitude.track(eventName, eventProperties);
    devLog("Amplitude Track", eventName, eventProperties);
  } catch (error) {
    devLog("Amplitude Track", "Failed to track Amplitude event:", error, true);
  }
}

/**
 * Identify a user in Amplitude.
 * Currently supports device/session-based tracking.
 * Can be extended in the future to support user-based identification.
 * @param userId - Optional user ID (if not provided, uses device ID)
 * @param userProperties - Optional user properties to set
 */
export function identify(userId?: string, userProperties?: Record<string, unknown>): void {
  if (!isInitialized) {
    return;
  }

  try {
    devLog("Amplitude Identify", userId, userProperties);

    if (userId) {
      amplitude.setUserId(userId);
    }

    if (userProperties) {
      const identifyObj = new amplitude.Identify();
      Object.entries(userProperties).forEach(([key, value]) => {
        // Amplitude accepts string, number, boolean, or array of these types
        if (typeof value === "string" || typeof value === "number" || typeof value === "boolean" || Array.isArray(value)) {
          identifyObj.set(key, value);
        }
      });
      amplitude.identify(identifyObj);
    } else if (userId) {
      // If only userId is provided, still call identify to set the user
      amplitude.identify(new amplitude.Identify());
    }
  } catch (error) {
    console.error("Failed to identify user in Amplitude:", error);
  }
}

/**
 * Clear user identification (e.g., on logout).
 */
export function clearUser(): void {
  if (!isInitialized) {
    return;
  }

  try {
    amplitude.setUserId(undefined);
    devLog("Amplitude Clear User");
  } catch (error) {
    console.error("Failed to clear user in Amplitude:", error);
  }
}
