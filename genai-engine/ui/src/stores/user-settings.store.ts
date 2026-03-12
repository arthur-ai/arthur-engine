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
  use24Hour: boolean;
  setUse24Hour: (use24Hour: boolean) => void;
}

export const useUserSettingsStore = create<UserSettingsState>()(
  devtools(
    persist(
      (set) => ({
        timezone: getDefaultTimezone(),
        setTimezone: (timezone) => set({ timezone }, false, "user-settings/setTimezone"),
        use24Hour: true,
        setUse24Hour: (use24Hour) => set({ use24Hour }, false, "user-settings/setUse24Hour"),
      }),
      { name: "arthur-user-settings" }
    ),
    { name: "user-settings-store" }
  )
);
