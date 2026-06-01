import { createStore, type StoreApi } from "zustand/vanilla";

import type { PreparationHook, TourPlugin } from "../core/types";

export interface PreparationRegistryStore {
  hooks: Map<string, PreparationHook>;
  register: (key: string, hook: PreparationHook) => void;
  unregister: (key: string) => void;
}

export interface TourPreparationPlugin extends TourPlugin {
  readonly store: StoreApi<PreparationRegistryStore>;
  /**
   * Imperative registration — convenience for consumers that want to wire a
   * preparation hook from outside React (e.g. in a service module). React
   * consumers should prefer the `useRegisterPreparation()` hook so cleanup
   * happens on unmount.
   */
  register: (key: string, hook: PreparationHook) => void;
  unregister: (key: string) => void;
  getHook: (key: string) => PreparationHook | undefined;
}

/**
 * Scoped Zustand-backed registry for step preparation hooks. The engine reads
 * from the registry at step-enter time via `engineStore.preparations` (the
 * plugin mirrors writes there so the engine can look hooks up without
 * importing this plugin). The plugin's own store powers reactive consumers
 * (e.g. dev panels that visualize which preps are registered).
 *
 * Replaces v0's `tracesTourPrep.ts` global mutable singleton — every consumer
 * goes through the engine's plugin contract instead of writing to module
 * state.
 */
export function createPreparationPlugin(): TourPreparationPlugin {
  const store = createStore<PreparationRegistryStore>((set, get) => ({
    hooks: new Map<string, PreparationHook>(),
    register: (key, hook) => {
      const next = new Map(get().hooks);
      next.set(key, hook);
      set({ hooks: next });
    },
    unregister: (key) => {
      const cur = get().hooks;
      if (!cur.has(key)) return;
      const next = new Map(cur);
      next.delete(key);
      set({ hooks: next });
    },
  }));

  return {
    name: "preparation",
    store,
    register: (key, hook) => store.getState().register(key, hook),
    unregister: (key) => store.getState().unregister(key),
    getHook: (key) => store.getState().hooks.get(key),
    install: ({ store: engineStore }) => {
      // Mirror plugin registry writes into the engine store's `preparations`
      // map so the engine's step-enter code path can look hooks up via
      // `store.preparations.get(key)` without needing a reference to this
      // plugin. We subscribe to keep the two in sync — including for hooks
      // registered after the engine starts (e.g. once `TourHost` mounts).
      const unsubscribe = store.subscribe((snapshot, prev) => {
        if (snapshot.hooks === prev.hooks) return;
        // Reconcile: take the latest registry and reflect it onto the engine
        // store. We don't try to be cute about deltas — the registry is
        // small (handful of preps) and changes are infrequent.
        const engineState = engineStore.getState();
        // Remove keys no longer registered.
        for (const key of Array.from(engineState.preparations.keys())) {
          if (!snapshot.hooks.has(key)) engineState.unregisterPreparation(key);
        }
        for (const [key, hook] of snapshot.hooks.entries()) {
          if (engineState.preparations.get(key) !== hook) engineState.registerPreparation(key, hook);
        }
      });
      // Seed the engine store with anything registered before install.
      const initialHooks = store.getState().hooks;
      const engineState = engineStore.getState();
      for (const [key, hook] of initialHooks.entries()) {
        engineState.registerPreparation(key, hook);
      }
      return () => {
        unsubscribe();
        const eng = engineStore.getState();
        for (const key of Array.from(store.getState().hooks.keys())) {
          eng.unregisterPreparation(key);
        }
      };
    },
  };
}
