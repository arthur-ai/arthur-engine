import { createStore, type StoreApi } from "zustand/vanilla";

import type { HighlightRenderer, OccluderDescriptor, PreparationHook, QueryHookResolver, TourEngineStore, TourState, TriggerFactory } from "./types";

/**
 * Default z-index ladder, overridable per `createTour({ layers: {...} })`.
 *
 * Tokens read directly via `useTourLayer(name)`: `spotlight`, `blocker`,
 * `panel`, `popover`. Two are reference points rather than direct readers:
 * `pulse` documents where the highlight ring sits (the task-tour renderer
 * derives it as the spotlight z-index + 1), and `certificate` is the ceiling
 * `tourDropdownTheme` lifts dropdowns above via `Math.max(...layers) + 1` —
 * keep it the maximum if you add tokens.
 */
export const DEFAULT_TOUR_LAYERS: Record<string, number> = {
  spotlight: 1399,
  pulse: 1400,
  blocker: 1401,
  panel: 1450,
  popover: 1500,
  certificate: 1600,
};

export interface CreateTourEngineStoreOptions {
  layers?: Record<string, number>;
  initialTriggers?: Record<string, TriggerFactory>;
}

/**
 * Create the per-tour Zustand store. Plugins, the engine itself, and React
 * consumers read/write through this single store — registries (triggers,
 * highlights, prep hooks, queryHooks) live as `Map` fields rather than nested
 * stores so subscribers don't pay the cost of cloning maps on every register.
 *
 * Registration mutates the map in place and bumps `state` only when the
 * actual `state` value changes; map subscribers don't need fine-grained
 * reactivity (the engine reads them imperatively at step-enter time).
 */
export function createTourEngineStore(options: CreateTourEngineStoreOptions = {}): StoreApi<TourEngineStore> {
  const { initialTriggers, layers } = options;
  return createStore<TourEngineStore>((set, get) => ({
    state: { status: "idle" } satisfies TourState,
    layers: { ...DEFAULT_TOUR_LAYERS, ...(layers ?? {}) },
    triggers: new Map(initialTriggers ? Object.entries(initialTriggers) : []),
    highlights: new Map<string, HighlightRenderer>(),
    preparations: new Map<string, PreparationHook>(),
    queryHooks: new Map<string, QueryHookResolver>(),
    occluders: new Map<string, OccluderDescriptor>(),

    setState: (next) => set({ state: next }),
    setLayer: (name, z) => set({ layers: { ...get().layers, [name]: z } }),

    // Map mutations are intentionally in-place. React consumers that need to
    // re-render on registry changes can subscribe to a more specific slice,
    // but the engine consumes these only at step-enter time so the cost of
    // forcing all subscribers to re-render on every register isn't worth it.
    registerTrigger: (key, factory) => {
      get().triggers.set(key, factory);
    },
    registerHighlight: (key, renderer) => {
      get().highlights.set(key, renderer);
    },
    registerPreparation: (key, hook) => {
      get().preparations.set(key, hook);
    },
    unregisterPreparation: (key) => {
      get().preparations.delete(key);
    },
    registerQueryHook: (hookId, resolver) => {
      get().queryHooks.set(hookId, resolver);
    },
    unregisterQueryHook: (hookId) => {
      get().queryHooks.delete(hookId);
    },
    registerOccluder: (descriptor) => {
      get().occluders.set(descriptor.id, descriptor);
    },
    unregisterOccluder: (id) => {
      get().occluders.delete(id);
    },
  }));
}
