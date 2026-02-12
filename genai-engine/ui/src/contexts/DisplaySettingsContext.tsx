import { useQuery } from "@tanstack/react-query";
import React, { createContext, useContext, ReactNode } from "react";

import { API_BASE_URL } from "@/lib/api";

export const DISPLAY_SETTINGS_QUERY_KEY = ["displaySettings"] as const;

interface DisplaySettings {
  default_currency: string;
}

const defaultDisplaySettings: DisplaySettings = { default_currency: "USD" };

async function fetchDisplaySettings(): Promise<DisplaySettings> {
  const res = await fetch(`${API_BASE_URL}/api/v2/display-settings`);
  if (!res.ok) return defaultDisplaySettings;
  const data = await res.json();
  return {
    default_currency: (data.default_currency ?? "USD").toString().trim().toUpperCase() || "USD",
  };
}

interface DisplaySettingsContextValue {
  defaultCurrency: string;
  isLoading: boolean;
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
  const { data = defaultDisplaySettings, isPending } = useQuery({
    queryKey: DISPLAY_SETTINGS_QUERY_KEY,
    queryFn: fetchDisplaySettings,
    staleTime: 5 * 60 * 1000,
  });

  const value: DisplaySettingsContextValue = {
    defaultCurrency: data.default_currency,
    isLoading: isPending,
  };

  return (
    <DisplaySettingsContext.Provider value={value}>
      {children}
    </DisplaySettingsContext.Provider>
  );
};
