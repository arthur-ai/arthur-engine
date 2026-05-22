import type { StepAdvanceEvent, TourPlugin } from "../core/types";

import type { PersistenceStorage } from "./createPersistencePlugin";

/**
 * String key used to identify a discrete unit of progress. Typically composed
 * from the section + step IDs (e.g. `"observe.chart"`), but the exact shape is
 * up to the caller via {@link CreateChecklistProgressPluginOptions.getKey}.
 */
export type ChecklistProgressKey = string;

/**
 * Reactive snapshot of progress. Always a fresh `ReadonlySet` reference when
 * any membership changes, so equality checks short-circuit no-op renders.
 */
export type ChecklistProgress = ReadonlySet<ChecklistProgressKey>;

export interface CreateChecklistProgressPluginOptions {
  /**
   * Storage key the progress set is persisted under. Use a unique-per-tour key
   * to avoid cross-pollination between tours.
   */
  storageKey: string;
  /**
   * Storage backend. Defaults to `window.localStorage`. Falls back to a noop
   * (no-persistence) if `localStorage` is unavailable (SSR, sandbox, etc.).
   */
  storage?: PersistenceStorage;
  /**
   * Maps a `step:advance` event onto a progress key. Defaults to
   * `"${sectionId}.${stepId}"`. Override when steps share IDs across sections,
   * or when stub-style sections need a different key shape.
   */
  getKey?: (event: StepAdvanceEvent) => ChecklistProgressKey;
  /**
   * Whether to clear progress on `tour:start`. Defaults to `false` so a
   * dismissed-then-resumed tour keeps its checkmarks across reloads. Set to
   * `true` when each fresh `start()` should wipe progress (e.g. completed-tour
   * replays).
   */
  resetOnStart?: boolean;
}

/**
 * Reactive view of the plugin. Consumers subscribe to `subscribe()` and read
 * with `getProgress()`; React hooks plug straight into `useSyncExternalStore`
 * against this shape.
 */
export interface ChecklistProgressPlugin extends TourPlugin {
  getProgress: () => ChecklistProgress;
  subscribe: (listener: (progress: ChecklistProgress) => void) => () => void;
  /** Add a key to progress. Idempotent. */
  add: (key: ChecklistProgressKey) => void;
  /** Remove a key from progress. */
  remove: (key: ChecklistProgressKey) => void;
  /** Toggle membership. Returns the new state for the key (true = present). */
  toggle: (key: ChecklistProgressKey) => boolean;
  /** Clear all progress. */
  reset: () => void;
}

const noopStorage: PersistenceStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

function resolveStorage(opts: { storage?: PersistenceStorage }): PersistenceStorage {
  if (opts.storage) return opts.storage;
  if (typeof window === "undefined") return noopStorage;
  try {
    return window.localStorage;
  } catch {
    return noopStorage;
  }
}

function parseProgress(raw: string | null): Set<ChecklistProgressKey> {
  if (!raw) return new Set();
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((value): value is string => typeof value === "string"));
  } catch {
    return new Set();
  }
}

function serializeProgress(progress: Set<ChecklistProgressKey>): string {
  return JSON.stringify([...progress]);
}

function setsEqual(a: Set<ChecklistProgressKey>, b: Set<ChecklistProgressKey>): boolean {
  if (a === b) return true;
  if (a.size !== b.size) return false;
  for (const value of a) {
    if (!b.has(value)) return false;
  }
  return true;
}

const defaultGetKey = (event: StepAdvanceEvent): ChecklistProgressKey => `${event.sectionId}.${event.stepId}`;

/**
 * Persists per-step progress (a string set) into a storage backend (defaults
 * to `window.localStorage`). Listens for tour bus events:
 *
 * - `step:advance` → adds `getKey(event)` to the set.
 * - `tour:start`   → clears the set when `resetOnStart` is `true`.
 *
 * The plugin is the single source of truth for item-level progress: React
 * consumers read state via {@link useChecklistProgress} (or `getProgress()` +
 * `subscribe()` directly), and never write to storage themselves. Cross-tab
 * synchronization via the `storage` event keeps multiple tabs in lock-step.
 *
 * @example
 * ```ts
 * const progressPlugin = createChecklistProgressPlugin({
 *   storageKey: "arthur:task-tour:progress",
 * });
 * const tour = createTour({ config: {...}, plugins: [progressPlugin] });
 * const progress = useChecklistProgress(progressPlugin);
 * progress.has("observe.chart"); // true after the engine advances past it
 * ```
 */
export function createChecklistProgressPlugin(opts: CreateChecklistProgressPluginOptions): ChecklistProgressPlugin {
  const storage = resolveStorage(opts);
  const getKey = opts.getKey ?? defaultGetKey;
  const resetOnStart = opts.resetOnStart ?? false;
  const listeners = new Set<(progress: ChecklistProgress) => void>();

  let current: Set<ChecklistProgressKey> = parseProgress(storage.getItem(opts.storageKey));

  const notify = (next: Set<ChecklistProgressKey>) => {
    if (setsEqual(next, current)) return;
    current = next;
    const snapshot: ChecklistProgress = current;
    listeners.forEach((l) => l(snapshot));
  };

  const writeProgress = (next: Set<ChecklistProgressKey>) => {
    try {
      storage.setItem(opts.storageKey, serializeProgress(next));
    } catch {
      // Storage may throw in private browsing mode; persistence is best-effort.
    }
    notify(next);
  };

  const add = (key: ChecklistProgressKey) => {
    if (current.has(key)) return;
    const next = new Set(current);
    next.add(key);
    writeProgress(next);
  };

  const remove = (key: ChecklistProgressKey) => {
    if (!current.has(key)) return;
    const next = new Set(current);
    next.delete(key);
    writeProgress(next);
  };

  const toggle = (key: ChecklistProgressKey): boolean => {
    const next = new Set(current);
    let nowPresent: boolean;
    if (next.has(key)) {
      next.delete(key);
      nowPresent = false;
    } else {
      next.add(key);
      nowPresent = true;
    }
    writeProgress(next);
    return nowPresent;
  };

  const reset = () => {
    if (current.size === 0) return;
    writeProgress(new Set());
  };

  return {
    name: "checklist-progress",
    getProgress: () => current,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    add,
    remove,
    toggle,
    reset,
    install: ({ bus }) => {
      const onAdvance = (event: StepAdvanceEvent) => {
        add(getKey(event));
      };
      const onStart = () => {
        if (resetOnStart) reset();
      };

      let detachStorage: (() => void) | undefined;
      if (typeof window !== "undefined") {
        const onStorage = (e: StorageEvent) => {
          if (e.key !== opts.storageKey) return;
          notify(parseProgress(e.newValue));
        };
        window.addEventListener("storage", onStorage);
        detachStorage = () => window.removeEventListener("storage", onStorage);
      }

      bus.on("step:advance", onAdvance);
      bus.on("tour:start", onStart);

      return () => {
        bus.off("step:advance", onAdvance);
        bus.off("tour:start", onStart);
        detachStorage?.();
      };
    },
  };
}
