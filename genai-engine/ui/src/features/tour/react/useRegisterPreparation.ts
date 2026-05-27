import { useEffect } from "react";

import type { PreparationHook } from "../core/types";

import { useTourEngine } from "./useTour";

/**
 * Register a preparation callback for the lifetime of the calling component.
 * Pair with a step `prepare: { key }` — the engine drives the hook through
 * the `<PreparationRunner />` widget mounted inside `TourHost` before it
 * resolves the step's target.
 *
 * The callback must not call React hooks. Read Query caches, refs, and Zustand
 * stores in the outer component/hook, then close over stable refs here. Wrap
 * each callback reference in `useCallback` / `useMemo` at the call site so
 * identity is stable.
 */
export function useRegisterPreparation(key: string, hook: PreparationHook): void {
  const engine = useTourEngine();
  useEffect(() => {
    engine.store.getState().registerPreparation(key, hook);
    return () => engine.store.getState().unregisterPreparation(key);
  }, [engine, key, hook]);
}
