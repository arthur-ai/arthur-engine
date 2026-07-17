import * as amplitude from "@amplitude/analytics-browser";

import { devLog, isAmplitudeDebugEnabled } from "./dev-log";
import type { AnalyticsEvents } from "./events";
import { createSessionReplayPlugin } from "./session-replay";

let isInitialized = false;

/**
 * Initialize Amplitude analytics (and, when configured, Session Replay).
 * Called once at app startup, before render. Analytics must never break the
 * app: missing config disables tracking with a console warning.
 */
export function initAnalytics(): void {
  // Idempotent: re-initializing the Browser SDK reassigns the device ID after
  // Session Replay has already locked onto the first one, which Amplitude
  // documents as the cause of event<->replay device ID mismatches. Guard
  // against repeat calls (HMR, remounts, accidental second call sites).
  if (isInitialized) {
    return;
  }

  const apiKey = import.meta.env.VITE_AMPLITUDE_TOKEN;

  if (!apiKey) {
    console.warn("VITE_AMPLITUDE_TOKEN not set. Amplitude tracking will be disabled.");
    return;
  }

  try {
    const replayPlugin = createSessionReplayPlugin();
    if (replayPlugin) {
      // Register the plugin before init so Session Replay and the analytics
      // SDK share the same device ID (per Amplitude's documented setup order).
      amplitude.add(replayPlugin);
    }

    amplitude.init(apiKey, {
      // `defaultTracking` is deprecated (SDK 2.10+) in favor of `autocapture`.
      // We enable only marketing attribution so UTM/referrer/click IDs are
      // captured as sticky user properties (utm_* + first-touch initial_utm_*)
      // that ride the whole funnel through to `onboarding/form_submitted`.
      // Everything else stays off to preserve the previous low-noise behavior;
      // an `autocapture` object leaves unspecified surfaces at their `true`
      // defaults, so each must be explicitly disabled.
      autocapture: {
        attribution: true,
        pageViews: false,
        sessions: false,
        formInteractions: false,
        fileDownloads: false,
        elementInteractions: false,
      },
      serverZone: "US",
      // Verbose SDK logging (incl. session-replay internals) only when
      // explicitly enabled via VITE_AMPLITUDE_DEBUG; otherwise warn-level.
      logLevel: isAmplitudeDebugEnabled() ? amplitude.Types.LogLevel.Debug : amplitude.Types.LogLevel.Warn,
    });
    isInitialized = true;
  } catch (error) {
    console.error("Failed to initialize Amplitude:", error);
  }
}

/**
 * Escape hatch for runtime-generated event names (the tour system forwards
 * its event bus as `task-tour.<type>`). Everything with a statically known
 * name must use `track` instead.
 */
export function trackDynamic(eventName: string, eventProperties?: Record<string, unknown>): void {
  if (!isInitialized) {
    devLog("Amplitude Track", `Amplitude is not initialized. Tried to track event ${eventName}.`, { eventName, eventProperties });
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
 * Track a known analytics event. The event name is checked against the
 * AnalyticsEvents catalog and the properties argument is required/forbidden
 * to match the event's declared shape.
 */
export function track<E extends keyof AnalyticsEvents>(
  event: E,
  ...args: AnalyticsEvents[E] extends undefined ? [] : [properties: AnalyticsEvents[E]]
): void {
  trackDynamic(event, args[0] as Record<string, unknown> | undefined);
}

/**
 * Identify a user in Amplitude.
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
 * Product-activation signals for the demo nurture playbook (path P4). Set as an
 * Amplitude user property so the "completed + activated" cohort can be built.
 */
export type ProductActivationReason = "own_agent_trace" | "self_hosted" | "own_data_experiment";

/**
 * PHASE 2 (playbook Section 4a `product_activated`): fixes the user-property
 * name up front so the Amplitude cohort can be authored, but is NOT yet wired
 * to a detection call site. Invoke it once the app can detect a user's own
 * agent trace, a self-hosted engine, or an experiment on their own data.
 */
export function markProductActivated(reason: ProductActivationReason): void {
  identify(undefined, { product_activated: true, product_activated_reason: reason });
}

/** Clear user identification (e.g., on logout). */
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
