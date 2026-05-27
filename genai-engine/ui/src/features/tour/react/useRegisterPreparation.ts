import { useEffect } from "react";

import type { PreparationHook } from "../core/types";

import { useTourEngine } from "./useTour";

/**
 * Register a preparation hook for the lifetime of the calling component.
 * Pair with a step `prepare: { key }` — the engine drives the hook through
 * the `<PreparationRunner />` widget mounted inside `TourHost` before it
 * resolves the step's target.
 *
 * Hooks are React-hook-shaped (see {@link PreparationHook}) so they can read
 * Query caches, refs, and Zustand stores. Wrap each hook reference in
 * `useCallback` / `useMemo` at the call site so identity is stable.
 */
export function useRegisterPreparation(key: string, hook: PreparationHook): void {
  const engine = useTourEngine();
  useEffect(() => {
    engine.store.getState().registerPreparation(key, hook);
    return () => engine.store.getState().unregisterPreparation(key);
  }, [engine, key, hook]);
}
