import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark" | "system";

export interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

export const useThemeStore = create<ThemeState>()(
  devtools(
    persist(
      (set) => ({
        mode: "system",
        setMode: (mode) => set({ mode }, false, "theme/setMode"),
      }),
      { name: "arthur-theme" }
    ),
    { name: "theme-store" }
  )
);
