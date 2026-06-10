import React, { createContext, useContext, ReactNode } from "react";

import { useApi } from "@/hooks/useApi";
import { useApiQuery } from "@/hooks/useApiQuery";
import { DisplaySettingsResponse } from "@/lib/api-client/api-client";
import { useUserSettingsStore } from "@/stores/user-settings.store";

/** Query key used by the display settings API call (for cache invalidation). */
export const DISPLAY_SETTINGS_QUERY_KEY = ["getDisplaySettingsApiV2DisplaySettingsGet"] as const;

const defaultDisplaySettings: DisplaySettingsResponse = { default_currency: "USD" };

interface DisplaySettingsContextValue {
  defaultCurrency: string;
  /** True only when BOTH server and user have chatbot enabled. */
  chatbotEnabled: boolean;
  /** Whether the server allows chatbot at all. */
  serverChatbotEnabled: boolean;
  enableChatbot: boolean;
  setEnableChatbot: (enableChatbot: boolean) => void;
  isLoading: boolean;
  timezone: string;
  setTimezone: (timezone: string) => void;
  use24Hour: boolean;
  setUse24Hour: (use24Hour: boolean) => void;
  /** URL of the Arthur Platform (Scope) for this deployment. Null if not configured. */
  scopeUrl: string | null;
}

const DisplaySettingsContext = createContext<DisplaySettingsContextValue | undefined>(undefined);

export const useDisplaySettings = () => {
  const ctx = useContext(DisplaySettingsContext);
  if (ctx === undefined) {
    throw new Error("useDisplaySettings must be used within DisplaySettingsProvider");
  }
  return ctx;
};

interface DisplaySettingsProviderProps {
  children: ReactNode;
}

export const DisplaySettingsProvider: React.FC<DisplaySettingsProviderProps> = ({ children }) => {
  const api = useApi();
  const { data, isPending } = useApiQuery<"getDisplaySettingsApiV2DisplaySettingsGet">({
    method: "getDisplaySettingsApiV2DisplaySettingsGet",
    args: [],
    enabled: !!api,
    queryOptions: { staleTime: 5 * 60 * 1000 },
  });
  const settings: DisplaySettingsResponse = data ?? defaultDisplaySettings;
  const timezone = useUserSettingsStore((s) => s.timezone);
  const setTimezone = useUserSettingsStore((s) => s.setTimezone);
  const use24Hour = useUserSettingsStore((s) => s.use24Hour);
  const setUse24Hour = useUserSettingsStore((s) => s.setUse24Hour);
  const enableChatbot = useUserSettingsStore((s) => s.enableChatbot);
  const setEnableChatbot = useUserSettingsStore((s) => s.setEnableChatbot);

  const serverChatbotEnabled = (settings as DisplaySettingsResponse & { chatbot_enabled?: boolean }).chatbot_enabled ?? true;

  const value: DisplaySettingsContextValue = {
    defaultCurrency: settings.default_currency ?? "USD",
    chatbotEnabled: serverChatbotEnabled && enableChatbot,
    serverChatbotEnabled,
    enableChatbot,
    setEnableChatbot,
    isLoading: isPending,
    timezone,
    setTimezone,
    use24Hour,
    setUse24Hour,
    scopeUrl: settings.scope_url ?? null,
  };

  return <DisplaySettingsContext.Provider value={value}>{children}</DisplaySettingsContext.Provider>;
};
