import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

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
        timezone: "UTC",
        setTimezone: (timezone) => set({ timezone }, false, "user-settings/setTimezone"),
        use24Hour: false,
        setUse24Hour: (use24Hour) => set({ use24Hour }, false, "user-settings/setUse24Hour"),
      }),
      { name: "arthur-user-settings" }
    ),
    { name: "user-settings-store" }
  )
);
