import type { TourPlugin } from "../core/types";

export type TourPersistenceStatus = "unseen" | "in-progress" | "dismissed" | "completed";

export interface PersistenceStorage {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
}

export interface CreatePersistencePluginOptions {
  /** Storage key written under. Use a unique-per-tour key to avoid cross-pollination. */
  storageKey: string;
  /**
   * Storage backend. Defaults to `window.localStorage`. Falls back to a noop
   * (no-persistence) if `localStorage` is unavailable (SSR, sandbox, etc.).
   */
  storage?: PersistenceStorage;
  /**
   * Whether to write the `"in-progress"` marker on `tour:start` / `tour:resume`.
   * Set to `false` if you only care about terminal states. Defaults to `true`.
   */
  trackInProgress?: boolean;
}

/**
 * Reactive view of the plugin's persistence layer. Consumers subscribe to
 * `subscribe()` and read with `getStatus()`; React hooks plug straight into
 * `useSyncExternalStore` against this shape.
 */
export interface TourPersistencePlugin extends TourPlugin {
  getStatus: () => TourPersistenceStatus;
  subscribe: (listener: (status: TourPersistenceStatus) => void) => () => void;
  /**
   * Imperative override — useful for "Reset tour" admin actions or a UI that
   * wants to force-mark the tour as `unseen` / `completed` outside of the
   * normal lifecycle. Writes to storage and notifies subscribers.
   */
  setStatus: (next: TourPersistenceStatus) => void;
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

function parseStatus(raw: string | null): TourPersistenceStatus {
  if (raw === "completed" || raw === "dismissed" || raw === "in-progress" || raw === "unseen") {
    return raw;
  }
  return "unseen";
}

/**
 * Reads the current persisted status for a given tour key. Safe to call
 * outside React. Returns `"unseen"` when no value has been written yet.
 */
export function readTourPersistence(storageKey: string, storage?: PersistenceStorage): TourPersistenceStatus {
  return parseStatus(resolveStorage({ storage }).getItem(storageKey));
}

/**
 * Writes a status into the persistence backend without going through the
 * engine. Useful when the consumer needs to update persistence directly
 * without instantiating a plugin (e.g. tests, admin reset UIs).
 *
 * For in-app use, prefer `plugin.setStatus(...)` so React subscribers are
 * notified.
 */
export function writeTourPersistence(storageKey: string, status: TourPersistenceStatus, storage?: PersistenceStorage): void {
  resolveStorage({ storage }).setItem(storageKey, status);
}

/**
 * Persists tour lifecycle into a storage backend (defaults to
 * `window.localStorage`). Listens for tour bus events:
 *
 * - `tour:start`   → `"in-progress"` (opt-out via `trackInProgress: false`)
 * - `tour:resume`  → `"in-progress"`
 * - `tour:dismiss` → `"dismissed"`
 * - `tour:end{completed}` → `"completed"`
 * - `tour:end{skipped}`   → `"dismissed"`
 *
 * The plugin is the single source of truth: React consumers read state via
 * {@link useTourPersistence} (or `getStatus()` + `subscribe()` directly), and
 * never write to storage themselves. Cross-tab synchronization via the
 * `storage` event keeps multiple tabs in lock-step.
 *
 * @example
 * ```ts
 * const persistencePlugin = createPersistencePlugin({ storageKey: "arthur:task-tour:status" });
 * const tour = createTour({ config: {...}, plugins: [persistencePlugin] });
 * const status = useTourPersistence(persistencePlugin);
 * ```
 */
export function createPersistencePlugin(opts: CreatePersistencePluginOptions): TourPersistencePlugin {
  const storage = resolveStorage(opts);
  const trackInProgress = opts.trackInProgress ?? true;
  const listeners = new Set<(status: TourPersistenceStatus) => void>();

  let current: TourPersistenceStatus = parseStatus(storage.getItem(opts.storageKey));

  const notify = (next: TourPersistenceStatus) => {
    if (next === current) return;
    current = next;
    listeners.forEach((l) => l(next));
  };

  const writeStatus = (next: TourPersistenceStatus) => {
    try {
      storage.setItem(opts.storageKey, next);
    } catch {
      // Storage may throw in private browsing mode; persistence is best-effort.
    }
    notify(next);
  };

  return {
    name: "persistence",
    getStatus: () => current,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    setStatus: writeStatus,
    install: ({ bus }) => {
      const onStart = () => {
        if (trackInProgress) writeStatus("in-progress");
      };
      const onResume = () => {
        if (trackInProgress) writeStatus("in-progress");
      };
      const onDismiss = () => writeStatus("dismissed");
      const onEnd = (event: { reason: "completed" | "skipped" }) => {
        writeStatus(event.reason === "completed" ? "completed" : "dismissed");
      };

      // Cross-tab sync: when another tab updates the same key, mirror it
      // into our in-memory state so subscribers re-render. Only attached when
      // we're using a real `window` and only for our specific key.
      let detachStorage: (() => void) | undefined;
      if (typeof window !== "undefined") {
        const onStorage = (e: StorageEvent) => {
          if (e.key !== opts.storageKey) return;
          notify(parseStatus(e.newValue));
        };
        window.addEventListener("storage", onStorage);
        detachStorage = () => window.removeEventListener("storage", onStorage);
      }

      bus.on("tour:start", onStart);
      bus.on("tour:resume", onResume);
      bus.on("tour:dismiss", onDismiss);
      bus.on("tour:end", onEnd);

      return () => {
        bus.off("tour:start", onStart);
        bus.off("tour:resume", onResume);
        bus.off("tour:dismiss", onDismiss);
        bus.off("tour:end", onEnd);
        detachStorage?.();
      };
    },
  };
}
