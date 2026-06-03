import { useEffect } from "react";

import type { QueryHookResolver } from "../core/types";

import { useTourEngine } from "./useTour";

/**
 * Register a queryHook resolver for the lifetime of the calling component.
 * Pair with a step `target: { kind: "queryHook", hookId }` — the engine
 * invokes the resolver synchronously when entering the step.
 *
 * The resolver is a plain function (not a React hook) so it can be called
 * from the engine without breaking the rules of hooks. Wrap it in
 * `useCallback` (or `useMemo`) at the call site so identity is stable.
 *
 * ```ts
 * const tracesTableRef = useRef<HTMLElement | null>(null);
 * useRegisterQueryHook("traces.firstRow", () => tracesTableRef.current?.querySelector("tbody tr") ?? null);
 * ```
 */
export function useRegisterQueryHook(hookId: string, resolver: QueryHookResolver): void {
  const engine = useTourEngine();
  useEffect(() => {
    engine.store.getState().registerQueryHook(hookId, resolver);
    return () => engine.store.getState().unregisterQueryHook(hookId);
  }, [engine, hookId, resolver]);
}
