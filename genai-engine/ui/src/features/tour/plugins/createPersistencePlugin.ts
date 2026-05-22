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
   * Whether to write the `"in-progress"` marker on `tour:start`. Set to `false`
   * if you only care about terminal states. Defaults to `true`.
   */
  trackInProgress?: boolean;
}

const noopStorage: PersistenceStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

function resolveStorage(opts: CreatePersistencePluginOptions): PersistenceStorage {
  if (opts.storage) return opts.storage;
  if (typeof window === "undefined") return noopStorage;
  try {
    return window.localStorage;
  } catch {
    return noopStorage;
  }
}

/**
 * Reads the current persisted status for a given tour key. Safe to call
 * outside React. Returns `"unseen"` when no value has been written yet.
 */
export function readTourPersistence(storageKey: string, storage?: PersistenceStorage): TourPersistenceStatus {
  const s = storage ?? resolveStorage({ storageKey });
  const raw = s.getItem(storageKey);
  if (raw === "completed" || raw === "dismissed" || raw === "in-progress" || raw === "unseen") {
    return raw;
  }
  return "unseen";
}

/**
 * Writes a status into the persistence backend without going through the
 * engine. Useful when an app surface (e.g. a "Reset tour" admin action or a
 * "Dismiss" handler in the UI) needs to update persistence directly.
 */
export function writeTourPersistence(storageKey: string, status: TourPersistenceStatus, storage?: PersistenceStorage): void {
  const s = storage ?? resolveStorage({ storageKey });
  s.setItem(storageKey, status);
}

/**
 * Persists tour lifecycle into a storage backend (defaults to
 * `window.localStorage`). Listens for `tour:start` (writes `"in-progress"`)
 * and `tour:end` (writes `"completed"` or `"dismissed"` depending on reason).
 *
 * The plugin only writes; the consuming feature reads via
 * {@link readTourPersistence} on mount to decide whether to auto-start or
 * render a resume affordance.
 *
 * @example
 * ```ts
 * const tour = createTour({
 *   config: {...},
 *   plugins: [createPersistencePlugin({ storageKey: "arthur:task-tour:status" })],
 * });
 * ```
 */
export function createPersistencePlugin(opts: CreatePersistencePluginOptions): TourPlugin {
  const storage = resolveStorage(opts);
  const trackInProgress = opts.trackInProgress ?? true;

  return {
    name: "persistence",
    install: ({ bus }) => {
      const onStart = () => {
        if (trackInProgress) {
          try {
            storage.setItem(opts.storageKey, "in-progress");
          } catch {
            // Storage may throw in private browsing mode; persistence is best-effort.
          }
        }
      };
      const onEnd = (event: { reason: "completed" | "skipped" }) => {
        try {
          storage.setItem(opts.storageKey, event.reason === "completed" ? "completed" : "dismissed");
        } catch {
          // Best-effort persistence; see above.
        }
      };

      bus.on("tour:start", onStart);
      bus.on("tour:end", onEnd);
      return () => {
        bus.off("tour:start", onStart);
        bus.off("tour:end", onEnd);
      };
    },
  };
}
