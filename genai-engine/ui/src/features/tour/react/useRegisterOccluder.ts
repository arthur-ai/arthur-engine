import { useEffect } from "react";

import type { OccluderDescriptor } from "../core/types";

import { useTourEngine } from "./useTour";

/**
 * Register a dismissible UI surface (modal / drawer / side panel / popover) so
 * the engine can reconcile it closed — and optionally open — on every step
 * entry. Pair with a step's `surfaces: { open: [{ id }] }` to keep the surface
 * open for steps that need it; every other step closes it, so a panel left
 * open by a prior step (or by the user) can't occlude the next step's target.
 *
 * The descriptor callbacks must not call React hooks. Read refs / Zustand /
 * nuqs state in the owning component and close over stable refs here. Wrap the
 * `descriptor` in `useMemo` at the call site so its identity is stable —
 * otherwise the registry Map churns on every render.
 */
export function useRegisterOccluder(descriptor: OccluderDescriptor): void {
  const engine = useTourEngine();
  useEffect(() => {
    engine.store.getState().registerOccluder(descriptor);
    return () => engine.store.getState().unregisterOccluder(descriptor.id);
  }, [engine, descriptor]);
}
