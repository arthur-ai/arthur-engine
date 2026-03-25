import type { ModelProvider } from "@/lib/api-client/api-client";

export interface UserSettings {
  timezone?: string;
  use24Hour?: boolean;
  enableChatbot?: boolean;
  chatbotModelProvider?: ModelProvider | "";
  chatbotModelName?: string;
  blacklistEndpoints?: string[];
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
  /** Available model providers for chatbot config. */
  enabledProviders?: ModelProvider[];
  /** Map of provider to available model names. */
  availableModelsMap?: Map<ModelProvider, string[]>;
  /** All available chatbot endpoints for the blacklist selector. */
  availableEndpoints?: string[];
  title?: string;
  saveLabel?: string;
  /** Shown on Save button when isSaving is true. */
  savingLabel?: string;
  cancelLabel?: string;
  timezoneLabel?: string;
  timeFormatLabel?: string;
}
