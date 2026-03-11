import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

function getDefaultTimezone(): string {
  if (typeof Intl !== "undefined" && typeof Intl.DateTimeFormat !== "undefined") {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return "UTC";
    }
  }
  return "UTC";
}

export interface UserSettingsState {
  timezone: string;
  setTimezone: (timezone: string) => void;
}

export const useUserSettingsStore = create<UserSettingsState>()(
  devtools(
    persist(
      (set) => ({
        timezone: getDefaultTimezone(),
        setTimezone: (timezone) => set({ timezone }, false, "user-settings/setTimezone"),
      }),
      { name: "arthur-user-settings" }
    ),
    { name: "user-settings-store" }
  )
);
