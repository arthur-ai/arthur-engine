import { useSyncExternalStore } from "react";

import type { ChecklistProgress, ChecklistProgressPlugin } from "../plugins/createChecklistProgressPlugin";

/**
 * Read the current progress set from a {@link ChecklistProgressPlugin}.
 * Subscribes via `useSyncExternalStore` so React re-renders whenever the
 * plugin records a new advance, the consumer calls `add`/`remove`/`toggle`,
 * or another tab writes to the same storage key.
 *
 * The plugin instance is the single source of truth — never write to storage
 * from React directly. Use the plugin's imperative methods (`add`, `remove`,
 * `toggle`, `reset`) for explicit edits.
 */
export function useChecklistProgress(plugin: ChecklistProgressPlugin): ChecklistProgress {
  return useSyncExternalStore(plugin.subscribe, plugin.getProgress, plugin.getProgress);
}
