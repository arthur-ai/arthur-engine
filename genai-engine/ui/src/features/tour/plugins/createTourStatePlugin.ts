import { createStore, type StoreApi } from "zustand/vanilla";

import type { SectionConfig, StepCompletedEvent, StepConfig, TourConfig, TourPlugin } from "../core/types";

/**
 * Persistence-aware status. Renamed from v0's "in-progress"/"unseen" four-state
 * union to be discriminated against the engine state — these reflect the
 * *user's relationship to the tour* (have they seen it? finished it?), not
 * the engine's runtime status.
 */
export type TourStateStatus = "unseen" | "in-progress" | "dismissed" | "completed" | "skipped";

export interface TourStateSnapshot {
  status: TourStateStatus;
  /**
   * Where the user was when last seen. Mirrors the engine's `dismissed`
   * position shape so `resumePosition()` is a trivial pluck.
   */
  position?: { sectionId: string; stepId?: string; boundary?: "sectionComplete" };
  /**
   * Set of completed step keys (sectionId.stepId). v0 split this into a
   * separate plugin; in v1 status and progress share one storage record.
   */
  completed: ReadonlySet<string>;
  /**
   * Whether the checklist panel is collapsed to its compact card. Persisted
   * alongside the rest of the tour state so the user's explicit collapse /
   * expand choice survives section navigation, remounts, reloads, and cross-
   * tab sync. Defaults to `true` (collapsed) for a fresh tour.
   */
  minimized: boolean;
}

export interface PersistenceStorage {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
}

const noopStorage: PersistenceStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

function resolveStorage(storage: PersistenceStorage | undefined): PersistenceStorage {
  if (storage) return storage;
  if (typeof window === "undefined") return noopStorage;
  try {
    return window.localStorage;
  } catch {
    return noopStorage;
  }
}

interface SerializedSnapshot {
  status: TourStateStatus;
  position?: { sectionId: string; stepId?: string; boundary?: "sectionComplete" };
  completed: string[];
  minimized: boolean;
}

function parseSnapshot(raw: string | null): TourStateSnapshot {
  if (!raw) return { status: "unseen", completed: new Set(), minimized: true };
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return { status: "unseen", completed: new Set(), minimized: true };
    }
    const obj = parsed as Partial<SerializedSnapshot>;
    const status: TourStateStatus =
      obj.status === "unseen" || obj.status === "in-progress" || obj.status === "dismissed" || obj.status === "completed" || obj.status === "skipped"
        ? obj.status
        : "unseen";
    const completed = new Set<string>((obj.completed ?? []).filter((v): v is string => typeof v === "string"));
    const minimized = typeof obj.minimized === "boolean" ? obj.minimized : true;
    const position =
      obj.position && typeof obj.position === "object" && typeof obj.position.sectionId === "string"
        ? {
            sectionId: obj.position.sectionId,
            stepId: typeof obj.position.stepId === "string" ? obj.position.stepId : undefined,
            boundary: obj.position.boundary === "sectionComplete" ? obj.position.boundary : undefined,
          }
        : undefined;
    return { status, position, completed, minimized };
  } catch {
    return { status: "unseen", completed: new Set(), minimized: true };
  }
}

function serializeSnapshot(snapshot: TourStateSnapshot): string {
  const payload: SerializedSnapshot = {
    status: snapshot.status,
    completed: Array.from(snapshot.completed),
    minimized: snapshot.minimized,
    ...(snapshot.position ? { position: snapshot.position } : {}),
  };
  return JSON.stringify(payload);
}

function snapshotsEqual(a: TourStateSnapshot, b: TourStateSnapshot): boolean {
  if (a.status !== b.status) return false;
  if ((a.position?.sectionId ?? null) !== (b.position?.sectionId ?? null)) return false;
  if ((a.position?.stepId ?? null) !== (b.position?.stepId ?? null)) return false;
  if ((a.position?.boundary ?? null) !== (b.position?.boundary ?? null)) return false;
  if (a.minimized !== b.minimized) return false;
  if (a.completed.size !== b.completed.size) return false;
  for (const v of a.completed) if (!b.completed.has(v)) return false;
  return true;
}

export interface TourStateStore {
  snapshot: TourStateSnapshot;
  setSnapshot: (next: TourStateSnapshot) => void;
}

export interface CreateTourStatePluginOptions {
  storageKey: string;
  storage?: PersistenceStorage;
  /**
   * Maps `step:completed` events to a progress key. Defaults to
   * `${sectionId}.${stepId}`. Override when sections + steps need a custom
   * shape (e.g. for cross-section step IDs).
   */
  getKey?: (event: StepCompletedEvent) => string;
  /**
   * Optional override for custom resume semantics. When omitted,
   * `resumePosition()` derives each stored step key with `getKey`.
   */
  isStepComplete?: (section: SectionConfig, step: StepConfig, completed: ReadonlySet<string>) => boolean;
}

export interface TourStatePlugin extends TourPlugin {
  readonly store: StoreApi<TourStateStore>;
  getSnapshot: () => TourStateSnapshot;
  setSnapshot: (next: Partial<TourStateSnapshot>) => void;
  /**
   * Mark a step (or arbitrary key) as completed without going through the
   * engine. Useful for admin reset UIs or migration.
   */
  markCompleted: (key: string) => void;
  unmarkCompleted: (key: string) => void;
  reset: () => void;
  /**
   * Compute the first incomplete step position based on the persisted
   * `completed` set and the supplied config. Returns the section-only
   * position when the section has no steps; `null` when every section/step
   * is recorded.
   */
  resumePosition: (config: TourConfig) => { sectionId: string; stepId?: string } | null;
}

const defaultGetKey = (event: StepCompletedEvent): string => `${event.sectionId}.${event.stepId}`;

/**
 * v1 single-record persistence + progress plugin. Owns its own Zustand store
 * scoped to the plugin instance; subscribers use `useTourPluginStore(plugin,
 * selector)` to read slices reactively. Writes are mirrored to a storage
 * backend (defaults to `localStorage`) on every mutation, and cross-tab
 * `storage` events are merged back into the store so multiple windows stay
 * in lock-step.
 */
export function createTourStatePlugin(opts: CreateTourStatePluginOptions): TourStatePlugin {
  const storage = resolveStorage(opts.storage);
  const getKey = opts.getKey ?? defaultGetKey;
  const isStepComplete = opts.isStepComplete;

  const initial = parseSnapshot(storage.getItem(opts.storageKey));

  const store = createStore<TourStateStore>((set) => ({
    snapshot: initial,
    setSnapshot: (next) => set({ snapshot: next }),
  }));

  const writeSnapshot = (next: TourStateSnapshot) => {
    const current = store.getState().snapshot;
    if (snapshotsEqual(current, next)) return;
    try {
      storage.setItem(opts.storageKey, serializeSnapshot(next));
    } catch {
      // Best-effort — private browsing may throw on writes.
    }
    store.getState().setSnapshot(next);
  };

  const merge = (patch: Partial<TourStateSnapshot>): TourStateSnapshot => {
    const current = store.getState().snapshot;
    return {
      status: patch.status ?? current.status,
      position: patch.position === undefined ? current.position : patch.position,
      completed: patch.completed ?? current.completed,
      minimized: patch.minimized ?? current.minimized,
    };
  };

  const setStatus = (status: TourStateStatus) => {
    if (store.getState().snapshot.status === status) return;
    writeSnapshot(merge({ status }));
  };

  const setPosition = (position: { sectionId: string; stepId?: string; boundary?: "sectionComplete" } | undefined) => {
    writeSnapshot(merge({ position }));
  };

  const markCompleted = (key: string) => {
    const completed = store.getState().snapshot.completed;
    if (completed.has(key)) return;
    const next = new Set(completed);
    next.add(key);
    writeSnapshot(merge({ completed: next }));
  };

  const unmarkCompleted = (key: string) => {
    const completed = store.getState().snapshot.completed;
    if (!completed.has(key)) return;
    const next = new Set(completed);
    next.delete(key);
    writeSnapshot(merge({ completed: next }));
  };

  const reset = () => {
    writeSnapshot({ status: "unseen", completed: new Set(), minimized: true });
  };

  const resumePosition: TourStatePlugin["resumePosition"] = (config) => {
    const completed = store.getState().snapshot.completed;
    const totalSteps = config.sections.reduce((acc, section) => acc + section.steps.length, 0);
    let globalStepIndex = 0;
    for (let sectionIndex = 0; sectionIndex < config.sections.length; sectionIndex++) {
      const section = config.sections[sectionIndex];
      if (section.steps.length === 0) {
        // Intro-only — count it complete only if its synthetic intro key was
        // recorded. The convention is "${sectionId}.__intro" but consumers
        // can override via getKey + manual markCompleted; default heuristic
        // is "section is done if any completed key starts with sectionId.".
        const sectionTouched = Array.from(completed).some((k) => k === `${section.id}.__intro` || k.startsWith(`${section.id}.`));
        if (!sectionTouched) return { sectionId: section.id };
        continue;
      }
      for (let stepIndex = 0; stepIndex < section.steps.length; stepIndex++) {
        const step = section.steps[stepIndex];
        const stepComplete =
          isStepComplete?.(section, step, completed) ??
          completed.has(
            getKey({
              tourId: config.id,
              sectionId: section.id,
              stepId: step.id,
              index: { sectionIndex, stepIndex, globalStepIndex, totalSteps },
              cause: "next",
            })
          );
        if (!stepComplete) {
          return { sectionId: section.id, stepId: step.id };
        }
        globalStepIndex++;
      }
    }
    return null;
  };

  return {
    name: "tour-state",
    store,
    getSnapshot: () => store.getState().snapshot,
    setSnapshot: (patch) => writeSnapshot(merge(patch)),
    markCompleted,
    unmarkCompleted,
    reset,
    resumePosition,
    install: ({ bus }) => {
      const onStart = () => setStatus("in-progress");
      const onResume = () => setStatus("in-progress");
      const onDismiss = () => setStatus("dismissed");
      const onEnd = (event: { reason: "completed" | "skipped" }) => {
        setStatus(event.reason === "completed" ? "completed" : "skipped");
      };
      const onStepEnter = (event: { sectionId: string; stepId: string }) => {
        setPosition({ sectionId: event.sectionId, stepId: event.stepId });
      };
      const onIntroShow = (event: { sectionId: string }) => {
        setPosition({ sectionId: event.sectionId });
      };
      const onSectionComplete = (event: { sectionId: string }) => {
        setPosition({ sectionId: event.sectionId, boundary: "sectionComplete" });
      };
      const onCompleted = (event: StepCompletedEvent) => {
        markCompleted(getKey(event));
      };
      const onIntroAck = (event: { sectionId: string }) => {
        // Intro-only sections never emit a step:completed (no steps), so we
        // synthesize a marker so `resumePosition` can advance past them. We
        // use the convention `${sectionId}.__intro` so consumers don't have
        // to special-case stub sections.
        markCompleted(`${event.sectionId}.__intro`);
      };

      let detachStorage: (() => void) | undefined;
      if (typeof window !== "undefined") {
        const onStorage = (e: StorageEvent) => {
          if (e.key !== opts.storageKey) return;
          writeSnapshot(parseSnapshot(e.newValue));
        };
        window.addEventListener("storage", onStorage);
        detachStorage = () => window.removeEventListener("storage", onStorage);
      }

      bus.on("tour:start", onStart);
      bus.on("tour:resume", onResume);
      bus.on("tour:dismiss", onDismiss);
      bus.on("tour:end", onEnd);
      bus.on("step:enter", onStepEnter);
      bus.on("section:intro:show", onIntroShow);
      bus.on("section:complete", onSectionComplete);
      bus.on("section:intro:acknowledge", onIntroAck);
      bus.on("step:completed", onCompleted);

      return () => {
        bus.off("tour:start", onStart);
        bus.off("tour:resume", onResume);
        bus.off("tour:dismiss", onDismiss);
        bus.off("tour:end", onEnd);
        bus.off("step:enter", onStepEnter);
        bus.off("section:intro:show", onIntroShow);
        bus.off("section:complete", onSectionComplete);
        bus.off("section:intro:acknowledge", onIntroAck);
        bus.off("step:completed", onCompleted);
        detachStorage?.();
      };
    },
  };
}
