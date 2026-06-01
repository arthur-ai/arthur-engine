import { useStore } from "zustand";
import type { StoreApi } from "zustand/vanilla";

/**
 * Read a slice of a plugin's scoped Zustand store. The plugin instance must
 * carry a `store` field — every v1 built-in plugin (`tour-state`,
 * `preparation`) does. Falls back to the default selector when none is given.
 *
 * Example:
 * ```ts
 * const completed = useTourPluginStore(statePlugin, s => s.snapshot.completed);
 * ```
 */
export function useTourPluginStore<S, T>(plugin: { store: StoreApi<S> }, selector: (state: S) => T): T {
  return useStore(plugin.store, selector);
}
