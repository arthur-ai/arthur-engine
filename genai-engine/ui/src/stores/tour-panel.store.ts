import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

/**
 * Open/closed state for the onboarding tour's docked side panel. This is a
 * pure UI concern — separate from tour progress (`arthur:task-tour:status`) —
 * so collapsing the panel never touches the engine's persisted position.
 *
 * Defaults to expanded so a freshly started tour shows its checklist; the
 * choice persists across reloads in its own `localStorage` key.
 */
export interface TourPanelState {
  collapsed: boolean;
  toggle: () => void;
  setCollapsed: (collapsed: boolean) => void;
}

export const useTourPanelStore = create<TourPanelState>()(
  devtools(
    persist(
      (set) => ({
        collapsed: false,
        toggle: () => set((state) => ({ collapsed: !state.collapsed }), false, "tourPanel/toggle"),
        setCollapsed: (collapsed) => set({ collapsed }, false, "tourPanel/setCollapsed"),
      }),
      { name: "arthur-tour-panel" }
    ),
    { name: "tour-panel-store" }
  )
);
