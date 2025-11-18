import * as amplitude from "@amplitude/analytics-browser";

let isInitialized = false;

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
    // Log in development mode only
    if (import.meta.env.DEV) {
      console.log("[Amplitude] Track:", eventName, eventProperties);
    }
    amplitude.track(eventName, eventProperties);
  } catch (error) {
    console.error("Failed to track Amplitude event:", error);
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
    // Log in development mode only
    if (import.meta.env.DEV) {
      console.log("[Amplitude] Identify:", userId, userProperties);
    }

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
    // Log in development mode only
    if (import.meta.env.DEV) {
      console.log("[Amplitude] Clear User");
    }
    amplitude.setUserId(undefined);
  } catch (error) {
    console.error("Failed to clear user in Amplitude:", error);
  }
}
