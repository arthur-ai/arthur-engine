export interface UserSettings {
  timezone?: string;
  use24Hour?: boolean;
  traceRetentionDays?: number;
  enableChatbot?: boolean;
  blacklistEndpoints?: string[];
  /** Instance-wide insights switch; only set when it changed. */
  insightsGenerationEnabled?: boolean;
}

export interface TimezoneOption {
  value: string;
  label: string;
}

export interface UserSettingsModalProps {
  open: boolean;
  onClose: () => void;
  initialSettings?: UserSettings;
  onSave: (settings: UserSettings) => void;
  /** When true, parent is fetching settings (e.g. on open). Save is disabled, form can show loading. */
  isLoading?: boolean;
  /** When true, parent is persisting after Save. Save and Cancel are disabled, button shows loading. */
  isSaving?: boolean;
  /** Override default timezone options. If not provided, built-in list is used. */
  timezoneOptions?: TimezoneOption[];
  /** Whether the server has chatbot enabled. Controls visibility of the AI Assistant section. */
  chatbotEnabled?: boolean;
  /** The default model provider and model, e.g. "openai · gpt-4.1-mini"; null when none is set. */
  defaultModelLabel?: string | null;
  /** Opens the Model Providers page, where the default model is set. */
  onOpenModelProviders?: () => void;
  /** All available chatbot endpoints for the blacklist selector. */
  availableEndpoints?: string[];
  /** Whether trace retention configuration is available. Controls visibility of the Application section. */
  traceRetentionEnabled?: boolean;
  /** Current trace retention value from the server. */
  initialTraceRetentionDays?: number;
  /** Allowed retention day values from the server. When empty, the retention selector is hidden. */
  allowedTraceRetentionDays?: number[];
  /** Whether the instance-wide insights switch can be shown (the application configuration loaded). */
  insightsGenerationAvailable?: boolean;
  /** Current instance-wide insights setting from the server. */
  initialInsightsGenerationEnabled?: boolean;
  /** Whether the application configuration is still loading. */
  isLoadingTraceRetention?: boolean;
  /** True for org-scoped tenant users; hides global-config subsections (chatbot, trace retention). */
  isTenant?: boolean;
  title?: string;
  saveLabel?: string;
  /** Shown on Save button when isSaving is true. */
  savingLabel?: string;
  cancelLabel?: string;
  timezoneLabel?: string;
  timeFormatLabel?: string;
}
