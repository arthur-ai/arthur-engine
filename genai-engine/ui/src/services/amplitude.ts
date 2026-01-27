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
  PROMPT_SAVED: "Prompt Saved",
  PROMPT_LOADED: "Prompt Loaded",
  PROMPT_RUN: "Prompt Run",
  PROMPT_PREVIEW: "Prompt Preview",
  EXPERIMENT_CONFIG_CREATED: "Experiment Config Created",
  EXPERIMENT_RUN_STARTED: "Experiment Run Started",
  MODEL_PARAMS_CHANGED: "Model Params Changed",
  TOOL_ADDED: "Tool Added",
  TOOL_REMOVED: "Tool Removed",
  OUTPUT_FIELD_CHANGED: "Output Field Changed",
  VARIABLE_VALUE_CHANGED: "Variable Value Changed",
  NOTEBOOK_LOADED: "Notebook Loaded",
  NOTEBOOK_SAVED: "Notebook Saved",
  NOTEBOOK_RENAMED: "Notebook Renamed",

  // Agent Experiments events
  AGENT_EXPERIMENT_INTENT_CREATE: "agent_experiment/intent_create",
  AGENT_EXPERIMENT_CREATED: "agent_experiment/created",
  AGENT_EXPERIMENT_DELETED: "agent_experiment/deleted",
  AGENT_EXPERIMENT_COPIED: "agent_experiment/copied",

  // Agent Notebooks events
  AGENT_NOTEBOOK_INTENT_CREATE: "agent_notebook/intent_create",
  AGENT_NOTEBOOK_INTENT_CANCEL: "agent_notebook/intent_cancel",
  AGENT_NOTEBOOK_CREATED: "agent_notebook/created",
  AGENT_NOTEBOOK_EXPERIMENT_RUN: "agent_notebook/experiment_run",
  AGENT_NOTEBOOK_LOAD_EXPERIMENT_CONFIG: "agent_notebook/load_experiment_config",
  AGENT_NOTEBOOK_SAVE: "agent_notebook/save",
  AGENT_NOTEBOOK_HISTORY_VIEW: "agent_notebook/history_view",
  AGENT_NOTEBOOK_DELETED: "agent_notebook/deleted",

  // Tracing events
  TRACING_LEVEL_CHANGED: "tracing/level_changed",
  TRACING_TIME_RANGE_CHANGED: "tracing/time_range_changed",
  TRACING_DRAWER_OPENED: "tracing/drawer_opened",
  TRACING_DRAWER_CLOSED: "tracing/drawer_closed",
  TRACING_DRAWER_SWITCH: "tracing/drawer_switch",
  TRACING_FILTERS_APPLIED: "tracing/filters_applied",
  TRACING_FILTERS_CLEARED: "tracing/filters_cleared",
  TRACING_FILTERS_FROM_URL_LOADED: "tracing/filters_from_url_loaded",
  TRACING_CONTENT_MODAL_OPENED: "tracing/content_modal_opened",
  TRACING_CONTENT_COPIED: "tracing/content_copied",
  TRACING_ID_COPIED: "tracing/id_copied",
  TRACING_REFRESH_METRICS_CLICKED: "tracing/refresh_metrics_clicked",
  TRACING_REFRESH_METRICS_RESULT: "tracing/refresh_metrics_result",

  // Dataset events
  DATASET_ADD_TO_DATASET_STARTED: "dataset/add_to_dataset_started",
  DATASET_SELECTED: "dataset/selected",
  DATASET_CREATED: "dataset/created",
  DATASET_TRANSFORM_SELECTED: "dataset/transform_selected",
  DATASET_TRANSFORM_SAVED: "dataset/transform_saved",
  DATASET_COLUMN_ADDED: "dataset/column_added",
  DATASET_ROW_ADDED: "dataset/row_added",
  DATASET_ROW_ADD_FAILED: "dataset/row_add_failed",

  // Feedback events
  FEEDBACK_OPENED: "feedback/opened",
  FEEDBACK_SUBMITTED: "feedback/submitted",
  FEEDBACK_CLEARED: "feedback/cleared",
  FEEDBACK_ERROR: "feedback/error",

  // Onboarding events
  ONBOARDING_API_KEY_CLICKED: "onboarding/api_key_clicked",
  ONBOARDING_TASK_ID_COPIED: "onboarding/task_id_copied",
  ONBOARDING_VIEW_TRACES_CLICKED: "onboarding/view_traces_clicked",
  ONBOARDING_SKIP_SETUP_CLICKED: "onboarding/skip_setup_clicked",

  // Cross-link events
  PLAYGROUND_OPEN_FROM_SPAN: "playground/open_from_span",
  CONTINUOUS_EVALS_NEW_FROM_TRACE: "continuous_evals/new_from_trace",

  // Model provider events
  MODEL_PROVIDER_CONFIGURE_OPENED: "model_provider/configure_opened",
  MODEL_PROVIDER_SAVED: "model_provider/saved",
  MODEL_PROVIDER_SAVE_FAILED: "model_provider/save_failed",
  MODEL_PROVIDER_DELETE_INTENT: "model_provider/delete_intent",
  MODEL_PROVIDER_DELETED: "model_provider/deleted",
  MODEL_PROVIDER_DELETE_FAILED: "model_provider/delete_failed",
  MODEL_PROVIDER_STATUS_CHANGED: "model_provider/status_changed",
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
