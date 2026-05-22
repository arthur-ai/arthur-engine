import { useSyncExternalStore } from "react";

import type { TourPersistencePlugin, TourPersistenceStatus } from "../plugins/createPersistencePlugin";

/**
 * Read the current persistence status from a {@link TourPersistencePlugin}.
 * Subscribes via `useSyncExternalStore` so React re-renders whenever the
 * plugin writes a new status (engine bus events, manual `setStatus(...)`,
 * cross-tab `storage` events).
 *
 * The plugin instance is the single source of truth for persistence — never
 * write to storage from React directly. Use `plugin.setStatus(...)` for
 * imperative overrides (admin reset, force-completion, etc.).
 */
export function useTourPersistence(plugin: TourPersistencePlugin): TourPersistenceStatus {
  return useSyncExternalStore(plugin.subscribe, plugin.getStatus, plugin.getStatus);
}
